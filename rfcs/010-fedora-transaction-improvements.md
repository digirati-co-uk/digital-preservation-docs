# RFC 010: Fedora transaction improvements

**Status: draft for discussion.** This paper steps back from the run of fixes to how imports use
Fedora transactions ([#350](https://github.com/digirati-co-uk/digital-preservation/issues/350),
[#383](https://github.com/digirati-co-uk/digital-preservation/pull/383)) and asks whether the
approach is sound, and what should change around it. It is written to be turned into issues on the
backlog board. Section 6 has indicative issue text for each proposal.

[RFC 010A: Ingress file management](010A-ingress-file-management.md) expands T12 into an early
delivery-and-capacity spike covering direct fetching, local-file sources and mixed deposits,
without changing the one-transaction-per-import model.

The short answer: **using one Fedora transaction per import job is the right model, and we should
keep it.** What hurts is the plumbing around it:
- the network path between our services and Fedora;
- how Fedora itself is deployed;
- how long, and how fragile, a large commit is;
- what happens when either side dies part-way through.

Most of those are cheap to fix. Several are configuration, not code.

The account of Fedora's behaviour here comes from reading its source at the versions we run:
- fcrepo **6.5.1**, the `fcrepo/fcrepo:6.5.1-tomcat9` image;
- the fcrepo-storage-ocfl **6.4.0** and ocfl-java **2.2.1** libraries it pins.

Links go to those tags. Where something is inferred rather than read in the code, it says so.
- **Section 7** asks whether we should go straight to Fedora 7 instead of upgrading within 6.x.
- **Section 9** lists what we haven't verified.

## 1. How an import works today

An import job is a list of things to do to one Archival Group: containers and binaries to add,
patch or delete. The Storage API importer runs it like this
([`ExecuteImportJob.cs`](https://github.com/digirati-co-uk/digital-preservation/blob/main/src/DigitalPreservation/Storage.API/Features/Import/Requests/ExecuteImportJob.cs)):

1. `POST /fcr:tx` to open a Fedora transaction. Then start a one-minute timer
   (`FedoraTransactionMonitor`) that keeps it alive with `POST /fcr:tx/{id}`.
2. Read the Archival Group (outside the transaction), or create it inside the transaction.
3. For each container to add: a `PUT`.
4. For each binary to add or patch:
   - stream the file from the deposit's S3 object, through the importer, to Fedora as a `PUT` with a
     `Digest: sha-256=…` header;
   - then `GET` the binary's description;
   - then, if it has no title yet, `PATCH` a title and `GET` it again;
   - then compare Fedora's checksum with ours.

   That's two to four sequential requests per file.
5. Deletes, then the Archival Group's own metadata.
6. `PUT /fcr:tx/{id}` to commit. That is one synchronous HTTP request, which returns when Fedora has
   finished writing everything.
7. If the commit's own response can't be trusted (a connection error, an ALB 502/503/504, or the
   monitor cancelling it), wait for the transaction to finish, then confirm the outcome from the
   Archival Group's OCFL version. This is #383.

Around that:
- **One importer task runs one job at a time.** It deletes the SQS message before starting, so there
  is no redelivery. A heartbeat and a reaper mark a job failed if the importer goes quiet.
- **The importer and Storage API reach Fedora through the platform's internet-facing ALB.** Traffic
  leaves the VPC through the NAT gateway and comes back in
  ([`docs/internals/deployment.md`, "Reaching Fedora"](https://github.com/digirati-co-uk/digital-preservation/blob/main/docs/internals/deployment.md)).
  That path's two timeouts produced the 2025 incidents behind #350:
  - the NAT gateway's fixed 350-second idle timeout;
  - the ALB's idle timeout, at its 4,000-second maximum.
- **S3 traffic from the private subnets uses an S3 gateway endpoint.** The shared VPC module that
  every environment uses creates it, so it isn't visible in preservation-ops itself. The importer's
  reads from the deposit bucket and Fedora's writes to the OCFL bucket therefore don't cross the NAT
  gateway. Only the importer→Fedora leg does.
- **Fedora is a single Fargate task**, `desired_count = 1`, behind that ALB. Its staging and OCFL temp
  directories are on an attached EBS volume.

## 2. What Fedora 6.5.1 actually does

### 2.1 During the transaction, nothing reaches S3

- **Every write is staged on Fedora's local disk.** A binary `PUT` copies the request body into a
  per-transaction directory under `fcrepo.ocfl.staging`
  ([`DefaultOcflObjectSession.writeResource`](https://github.com/fcrepo-exts/fcrepo-storage-ocfl/blob/fcrepo-storage-ocfl-6.4.0/src/main/java/org/fcrepo/storage/ocfl/DefaultOcflObjectSession.java#L159-L215)).
  Nothing goes to S3 until the commit.
- **Fedora checks the `Digest` header at `PUT` time,** after staging the bytes
  ([`AbstractNonRdfSourcePersister`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-persistence-ocfl/src/main/java/org/fcrepo/persistence/ocfl/impl/AbstractNonRdfSourcePersister.java#L80-L94)).
  A mismatch is a 409.
- **One failed request poisons the whole transaction.** Any exception during the request marks the
  transaction FAILED
  ([`FedoraBaseResource.doInDbTxWithRetry`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-http-api/src/main/java/org/fcrepo/http/api/FedoraBaseResource.java#L124-L146)),
  and a later commit is refused.
- **Writes to one OCFL object are serialised.** `writeResource` is `synchronized` on the object's
  session, and the body streams inside it. An Archival Group is one OCFL object, so **uploading files
  in parallel within one import would not be faster**: Fedora would run them one at a time.
- **A binary `PUT` holds a database connection while its body streams.**

### 2.2 Locks

- **A write anywhere inside an Archival Group takes an exclusive lock on the whole group**
  ([`AbstractService.lockArchivalGroupResource`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/services/AbstractService.java#L284-L309)).
  Only one transaction at a time can change a given group.
- **Locks are in memory, and a conflict doesn't wait.** It fails straight away with a 409
  ([`InMemoryResourceLockManager`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/lock/InMemoryResourceLockManager.java),
  `ConcurrentUpdateExceptionMapper`). Locks are released at the end of the commit or rollback.
- **Reads are not blocked.** A `GET` outside the transaction takes no lock, and sees the last
  committed version while an import is open or committing.

### 2.3 Expiry

- **A transaction expires after `fcrepo.session.timeout`**, which defaults to 3 minutes. The clock is
  measured from its last refresh.
- **The expiry is refreshed only in two ways:** at the *start* of each request that carries the
  transaction header
  ([`TransactionProvider`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-http-commons/src/main/java/org/fcrepo/http/commons/session/TransactionProvider.java#L62-L68)),
  or by `POST /fcr:tx/{id}`.
- **So a single file upload that takes longer than 3 minutes would let the transaction expire
  mid-upload, unless something refreshes it.** Our one-minute keep-alive timer is genuinely needed.
- **A scheduled clean-up runs every session-timeout period**
  ([`TransactionManagerImpl`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/TransactionManagerImpl.java#L89-L120)).
  It rolls back expired open transactions, and later removes finished ones.
- **Restarting Fedora discards every open transaction and all staged files.**

### 2.4 The commit, step by step

`PUT /fcr:tx/{id}` runs
[`TransactionImpl.commit()`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/TransactionImpl.java#L82-L121),
a `synchronized` method, on the request thread:

1. **Checks:** the transaction must not be expired or FAILED. Its state becomes COMMITTING. Its expiry
   is *not* extended for the commit.
2. **Database:** inside one database transaction
   ([`doCommitLongRunning`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/TransactionImpl.java#L349-L364)),
   move the transaction's rows into the main containment, reference, membership and search index
   tables. Cost scales with the number of resources.
3. **OCFL**, last. For each OCFL object, one at a time, ocfl-java `updateObject`:
   - **re-reads every staged file in full to compute its digest**, serially, and checks it against the
     digest recorded at `PUT` time
     ([`AddFileProcessor`](https://github.com/OCFL/ocfl-java/blob/v2.2.1/ocfl-java-core/src/main/java/io/ocfl/core/inventory/AddFileProcessor.java#L124-L147));
   - moves the files into `fcrepo.ocfl.temp`. That's a rename if it's on the same filesystem, which
     it is for us;
   - **uploads every file to S3**: up to `fcrepo.ocfl.s3.max_concurrency` (100) at once, with
     multipart upload for files of 8 MB or more
     ([`CloudStorage`](https://github.com/OCFL/ocfl-java/blob/v2.2.1/ocfl-java-core/src/main/java/io/ocfl/core/storage/cloud/CloudStorage.java#L240-L292));
   - writes the new inventory. Readers see the old version until the root inventory is replaced.
4. **The database transaction commits.** Then events are emitted and the locks released.

Fedora's own source warns that the database transaction stays open for the whole OCFL write, and that
the connection timeout may need raising for large commits. A commit holds two database connections
throughout: the Spring transaction, and ocfl-java's object-details connection. The pool default is
HikariCP's 10, and we don't set `fcrepo.db.max.pool.size`.

**What makes a big commit slow** is the full local re-read of every byte in step 3 and the S3 upload,
plus database work that scales with the number of files. Our October test was 2,797 binaries and
38.7 GB, and its commit took 22 minutes.

### 2.5 Failure, and what happens to the HTTP request

- **A failed commit is undone by compensation, not atomically.** The OCFL write either rolls back to
  the previous version or purges a new object, and the database transaction rolls back
  (`TransactionImpl.commit` catch block, then `rollback()`).
- **That can go wrong in three ways:**
  - **A failed rollback** is only logged ("must be manually remediated").
  - **A crash or kill mid-upload** can leave a half-written version directory in S3. The next write
    to that object then fails with `ObjectOutOfSyncException`, and **the Archival Group is wedged
    until someone removes the orphan by hand.**
  - **A crash after the root inventory is written but before the database commits** leaves OCFL ahead
    of Fedora's index, with no automatic reconciliation.
- **A client disconnect doesn't stop a commit.** It runs synchronously, and nothing in fcrepo checks
  whether the client is still connected. Only writing the response fails.

### 2.6 Asking Fedora about a transaction

How `GET /fcr:tx/{id}` behaves
([`Transactions.getTransactionStatus`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-http-api/src/main/java/org/fcrepo/http/api/Transactions.java#L61-L80)
→ [`TransactionManagerImpl.get`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/TransactionManagerImpl.java#L137-L157)):

| Situation | Answer |
|---|---|
| Open, or committing, within 3 minutes of the last refresh | **204**: the two cases look the same |
| Past expiry while a commit runs | `get()` calls `rollback()`, which is `synchronized` like `commit()`, so **the `GET` blocks until the commit ends**. Then 410 |
| Committed | 410, with body text "already committed" |
| Commit failed or rolled back | 410, with body text "rolled back" or "expired" |
| Removed by the clean-up task | 404 |

- **A `GET` never returns 409.** The 409s in the 2025 logs came from the keep-alive `POST`: its
  `updateExpiry()` is also `synchronized`, waits for the commit, then throws `TransactionClosedException`,
  which `TransactionRuntimeExceptionMapper` maps to 409.
- **So on any commit longer than 3 minutes, the monitor's 30-minute "status check" is in practice a
  second long request** that returns when the commit ends. It goes over the same ALB and NAT path, with
  the same failure modes. #383 now accounts for this.
- **Sending the commit `PUT` again, before expiry, returns the real outcome**: 204 if the first commit
  succeeded, 410 if it failed. That's only useful within the expiry window.

### 2.7 How the commit talks to S3, and why 6.5.2 is a step backwards for us

**Two S3 clients carry the upload.** Fedora gives ocfl-java two
([`OcflPersistentStorageUtils`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-persistence-ocfl/src/main/java/org/fcrepo/persistence/ocfl/impl/OcflPersistentStorageUtils.java#L131-L142)),
and ocfl-java picks one per file by size
([`OcflS3Client`](https://github.com/OCFL/ocfl-java/blob/v2.2.1/ocfl-java-aws/src/main/java/io/ocfl/aws/OcflS3Client.java#L180-L199)):
- **Files of 8 MB or more** go through the AWS CRT `S3TransferManager`, as parallel multipart uploads.
  The connection-pool settings below don't apply to them, and they handle files over 5 GB.
- **Files under 8 MB** go through the Netty client's `putObject`, sharing a pool of
  `fcrepo.ocfl.s3.max_concurrency` (100) connections. An upload that can't get a connection within the
  pool's *acquisition* timeout fails, and fails the commit. In 6.5.1 that timeout is set by
  `fcrepo.ocfl.s3.timeout.connection.seconds`, default 60.
- **S3-to-S3 `CopyObject`**, also on the Netty client, is used when a mutable head becomes a version
  (autoversioning off) and to copy the small inventory files. It isn't used for our versioned commits.

So for us, **the S3 exposure in 6.5.1 is a commit with thousands of small files**. Every upload is
submitted at once, queues behind 100 connections, and each gets 60 seconds to find one. The October
test (2,797 files) passed, so this is a margin, not an observed failure.

**What changed after 6.5.1:**

| Change | What it does | Released in |
|---|---|---|
| [FCREPO-4084](https://github.com/fcrepo/fcrepo/pull/2309), "Ocfl java s3 5gb issue" (fcrepo#2309) | Turns on multipart for the Netty client, so a `CopyObject` over 5 GB works (as `UploadPartCopy`). That matters for the mutable-head path, not ours | 6.5.2; on `main` after 7.0.0 |
| [fcrepo#2314](https://github.com/fcrepo/fcrepo/pull/2314) | Rewires `timeout.connection.seconds` to the TCP connect timeout. The acquisition timeout falls back to the AWS SDK default: **10 seconds, and no longer configurable** | 6.5.2; on `main` after 7.0.0 |
| [fcrepo#2327](https://github.com/fcrepo/fcrepo/pull/2327), backported as [#2328](https://github.com/fcrepo/fcrepo/pull/2328) | Restores a configurable acquisition timeout, `fcrepo.ocfl.s3.timeout.acquisition.seconds`, default 60. Upstream describes #2314's effect as a regression that users on 6.5.2 hit during commits under load | `main` (24 August 2026) and `6.5-maintenance` (9 October 2026). **Not yet released**; it will be in 6.5.3 |

**So 6.5.2 is likely worse for us than 6.5.1.** It cuts the small-file acquisition window from 60
seconds to a fixed 10, which is exactly our many-files case, and its other S3 change is for a path we
don't use. We should skip 6.5.2 (T4). The releases worth moving to are 6.5.3, or a 7.x release that
includes #2327 (section 7, T14).

**For [RFC 009](009-large-files.md):** files over 5 GB go through the CRT transfer manager at commit.
On the Fedora side, nothing here should stop them, on 6.5.1 or on 7.0.0. That's inferred from the
code and untested, so T14's test includes a file over 5 GB.

## 3. Is one transaction per import the right model?

Yes:
- it is the only way Fedora 6 gives **one OCFL version per import**, with a clean rollback when
  anything fails part-way;
- the group-level lock gives us **mutual exclusion per Archival Group** for free;
- reads carry on against the last committed version throughout.

The alternatives are all worse:

| Alternative | Why not |
|---|---|
| **Autoversioning off** (`fcrepo.autoversioning.enabled=false`), with writes going to an OCFL mutable head and versions made by `POST fcr:versions` | Every write lands in S3 straight away, so bytes move incrementally. But changes to a mutable head **cannot be rolled back**, a half-finished import is visible, `fcr:versions` is refused inside a transaction, and creating the version copies the mutable head with serial `CopyObject` calls, which are limited to 5 GB each |
| **Many smaller transactions per import** | Many OCFL versions per import, and a partly-applied import visible between them. That defeats the point of a version |
| **External content with `handling=proxy` or `redirect`** | Only a reference is stored in OCFL, not the bytes. This breaks the principle that the whole preservation state can be recovered from OCFL alone |
| **Write OCFL ourselves, then `POST /{path}/fcr:reindex`** | A large change. We would have to write Fedora's own OCFL layout, including its `.fcrepo` headers. With `fcrepo.ocfl.s3.db.enabled` on, which is the default and ours, ocfl-java caches inventories in the database, so writing behind Fedora's back puts it out of sync |

One variant may be worth having, if the spike in T12 and [RFC 010A](010A-ingress-file-management.md)
shows a gain once T1 has removed the NAT leg: **external content with `handling=copy`**. Fedora
fetches the bytes itself at `PUT` time, then stages, verifies and commits them exactly as for a
streamed `PUT`. The fetched stream goes through the same internal-binary path and digest check, so
nothing about the model changes. This is the TODO in `FedoraClient.MakeBinaryPut`, from the March
2024 prototype. On the Fedora we run, it can't use a presigned S3 URL, because Fedora sends a `HEAD`
first. fcrepo #2331, not yet released, fixes that. See T12.

## 4. Where it hurts

| # | Problem | Effect |
|---|---|---|
| P1 | Service traffic to Fedora goes out through NAT to an internet-facing ALB and back | The 350 s NAT idle drop and the 4,000 s ALB cap. Most of #350 and #383 exists to survive this. Fedora is also on an internet-facing load balancer when only our own services need it |
| P2 | Every ingested byte is relayed by the importer | S3 legs already use the gateway endpoint, so they don't cross NAT. But the importer holds a stream from S3 to Fedora for every binary, and before T1 that stream crosses the NAT gateway once on its way to Fedora. NAT data processing is charged per GB, about $0.05 in eu-west-1 at the time of writing |
| P3 | Fedora's ECS service uses default deployment settings and a strict health check | ECS defaults (minimum 100%, maximum 200%) should briefly run **two Fedoras** behind the ALB during a deploy: transactions live in one task's memory, and two tasks would write OCFL at once. The health check has a 10 s timeout and marks the task unhealthy after 2 failures 30 s apart. A slow health endpoint during a heavy commit could get Fedora replaced mid-commit, which is the "wedged Archival Group" case in 2.5 |
| P4 | Commit time scales with bytes, and includes a full local re-read | Long commits are the trigger for P1's timeouts, and they block the single importer (P7) |
| P5 | The S3 connection-pool acquisition timeout for files under 8 MB: 60 s on 6.5.1, a fixed 10 s on 6.5.2 | A commit with thousands of small files could fail waiting for a connection. Not observed on 6.5.1, since the October test passed, but 6.5.2 would make it more likely (2.7) |
| P6 | Importer death mid-commit is reported as a failure | Fedora finishes the commit, but the reaper marks the job failed. The deposit goes to Error while the Archival Group moved on, and a retry fails or makes a confusing extra version. Importer redeploys do this, and on dev every push to `main` redeploys it. #383 doesn't cover it |
| P7 | One importer runs jobs serially | A long import blocks every other deposit's import until it finishes |
| P8 | Two to four sequential HTTP requests per binary | Latency multiplied by thousands of files. The post-`PUT` checksum comparison is redundant, since Fedora already rejected a bad digest |
| P9 | Fedora runs with `-Dfcrepo.log=DEBUG` in every environment | Log volume, and some overhead, on every request |
| P10 | Possible stale cache for new resources after a long commit | *Inferred, untested.* Fedora invalidates its containment caches at the start of the commit, so a non-transaction read during the upload could cache "doesn't exist" for a new Archival Group, and keep returning 404 for up to 10 minutes after it lands while it keeps being polled. Our own outcome check reads the OCFL inventory from S3, so it isn't affected |

## 5. Proposals at a glance

| Id | Proposal | Repo | Size | Solves |
|---|---|---|---|---|
| T1 | Private network path from our services to Fedora | ops (+ platform config) | M | P1 |
| T2 | ~~S3 gateway VPC endpoint~~ Withdrawn: every environment already has one (section 1) | – | – | – |
| T3 | Fedora ECS deployment and health-check settings | ops | S | P3 |
| T4 | Skip Fedora 6.5.2, and widen the S3 acquisition timeout now | ops | XS | P5 |
| T5 | Evaluate `fcrepo.ocfl.unsafe.write.enabled` | ops (measure on dev) | S | P4 |
| T6 | Record a commit in progress, and reconcile instead of failing | platform | M | P6 |
| T7 | Fewer requests per binary | platform | S | P8 |
| T8 | Run import jobs for different Archival Groups concurrently | platform | M | P7 |
| T9 | Runbook: an Archival Group wedged by a half-written version | docs / ops | S | P3, 2.5 |
| T10 | Turn off Fedora debug logging in deployed environments | ops | XS | P9 |
| T11 | Spike: confirm or rule out the stale containment cache | platform | S | P10 |
| T12 | Spike, then possibly adopt: Fedora fetches file bytes itself (external content, `handling=copy`, presigned URL, needs fcrepo #2331) | platform + ops | M | P2 (partly) |
| T13 | After T1: simplify the transaction monitor | platform | S | P1 follow-up |
| T14 | Upgrade Fedora to 7.x | ops + platform (test) | M | Section 7, P5 |

**Suggested order:**
1. **First**, all quick:
   - T3, T4 and T10: configuration only, and each removes a real risk;
   - T11: a quick check.
2. **Then:** T1, the change that removes the timeouts at their root; and T5, measured on dev with a
   large deposit.
3. **Then:** T14, the move to Fedora 7. Re-run T5's measurements on 7. T12's spike can run on dev at
   any time ops can stand up a pinned 7.1 snapshot. T12 itself lands only on a release that contains
   #2331, and only if the spike shows a gain.
4. **Then:** T6, before T8 (concurrency makes reconciliation more important), and T7 any time.
5. **Later:** T9 alongside T3, and T13 once T1 has landed. Under option (a) the 4,000 s ALB cap
   remains, so #383's verification stays.

## 6. Indicative issue text

Each block below is meant to be pasted into an issue, more or less as is.

### T1: Reach Fedora on a private network path, not through NAT and the public ALB

**Problem.** The Storage API and importer reach Fedora through the platform's internet-facing ALB.
Traffic leaves the VPC through the NAT gateway and comes back in. That path has a fixed 350-second NAT
idle timeout, and the ALB's idle timeout is capped at 4,000 seconds. Together they caused the 2025
incidents in #350, and most of the commit-verification logic in #383 exists to survive them. Fedora
needn't be on an internet-facing load balancer at all.

**Proposal.** Give service-to-service traffic a private route to Fedora. Either:
- (a) **an internal ALB**: removes NAT, but keeps a 4,000 s idle cap, so commits over about 66
  minutes would still hit it; or
- (b) **service discovery** straight to the Fedora task. With **Cloud Map DNS-only** discovery there's
  no proxy and no load balancer, so no idle cap. But the task's IP changes on every deploy, there's no
  health-based routing beyond ECS deregistration, and the shared modules don't support it.
  **ECS Service Connect** is different: it adds a proxy to every task, with its own idle timeout
  (5 minutes by default for HTTP) and per-request timeout. Both can be set to 0, but it isn't cap-free
  by default. Fedora is a single task, so there's nothing to balance either way.

Point the importer's and Storage API's `Fedora__Root` at it. Decide whether anything still needs
Fedora on the public ALB, such as admin access, and if not, remove the listener rule.

**For option (a)**, the shared modules will support it: digirati-co-uk/terraform-aws-modules#100
(open at the time of writing; preservation-ops pins the modules at `v3.34`, so T1 needs a module
release or a branch ref) adds an `internal` option and an optional HTTPS listener to `wildcard-alb`,
and lets ECS services register with more than one target group. Donald used it to move Wellcome's
DLCS image servers onto an internal ALB with no downtime:
1. add an internal Route 53 hosted zone and an internal ALB;
2. put the service on both the old and new ALBs;
3. point its callers at the internal hostname;
4. remove it from the old ALB.

That pattern uses a private zone and plain HTTP inside the VPC, so `Fedora__Root` becomes an
`http://` URL. That's fine as long as it matches exactly, the same condition as in "Check before
switching". Keeping HTTPS with the existing wildcard certificate is the alternative, and a
sub-decision under D3. The ALB→Fedora hop is already plain HTTP today (the target group is
`HTTP` to port 8080), so the question is whether the services→ALB leg, now inside the VPC,
also carries basic auth in clear text. If HTTPS is kept, add one more check before switching:
whether Fedora's response URIs come back as `https://` behind the internal ALB, which depends on
how the image's Tomcat handles forwarded headers.

**Check before switching.** Fedora builds resource URIs from the request's host. Confirm that nothing
we persist holds full Fedora URLs: not the Storage or Preservation API databases, not the import job
JSON, not METS. Confirm too that the Storage API's URI conversion only depends on `Fedora__Root`.
Change both services in the same deploy.

**Acceptance.**
- No Fedora traffic from our services crosses the NAT gateway.
- On dev, a large commit returns its 204 directly. Under option (a), a commit past the 4,000 s ALB
  cap stays covered by #383's verification.
- `deployment.md`'s "Reaching Fedora" section is rewritten.
- TCP keepalive (120/30/5) stays, as dead-peer detection.

### T2: Withdrawn

This proposed an S3 gateway endpoint. Every environment already has one, created by the shared VPC
module (`terraform-aws-modules`, `tf/modules/vpc`, `public-private-igw/vpc_endpoints.tf`), which
isn't visible from preservation-ops alone. The id is kept so the other proposals' numbers don't
change.

### T3: Fedora ECS service: single-instance deployment and a tolerant health check

**Problem.**
- **Deploys.** The Fedora service sets `desired_count = 1`, but leaves ECS's deployment defaults in
  place (minimum healthy 100%, maximum 200%). During a deploy, a second Fedora task should start and
  register with the target group while the first is still serving. Transactions live in one task's
  memory, so requests carrying a transaction id can reach the wrong task and get 404. Two Fedoras would
  also be writing OCFL and the index database at the same time.
- **Health check.** The ALB health check (`fcr:systeminfo`) has a 10 s timeout and marks the task
  unhealthy after 2 failures 30 s apart, with no grace period. If that endpoint is slow during a heavy
  commit, ECS replaces the task mid-commit. A task killed mid-upload can leave an Archival Group wedged
  (see T9).

**Proposal.**
- Set `deployment_minimum_healthy_percent = 0` and `deployment_maximum_percent = 100` on the Fedora
  service. A deploy is then stop-then-start, with a short outage instead of two writers.
- Raise the health-check timeout and unhealthy threshold, for example 30 s and 5, and set
  `health_check_grace_period_seconds`.
- First, look in CloudWatch for `UnHealthyHostCount` on the Fedora target group during the 22-minute
  commit test on 6 October 2026, to see how close we've already come.
- Optionally set `deployment_circuit_breaker`.

**Acceptance.**
- A Fedora deploy on dev never shows two registered targets.
- No unhealthy-target events during a large commit on dev.

### T4: Skip Fedora 6.5.2, and widen the S3 acquisition timeout now

**Problem.** At commit, every file under 8 MB is uploaded through a pool of 100 S3 connections. An
upload that waits longer than the pool's acquisition timeout fails the commit (2.7). A deposit with
thousands of small files queues them all at once.
- **On 6.5.1**, which we run, that timeout is `fcrepo.ocfl.s3.timeout.connection.seconds`, default 60.
- **6.5.2** ([fcrepo#2314](https://github.com/fcrepo/fcrepo/pull/2314)) silently cuts it to the AWS SDK
  default of 10 seconds, with no setting to raise it again. Upstream fixed that in
  [fcrepo#2327](https://github.com/fcrepo/fcrepo/pull/2327), backported as #2328, but neither is
  released yet.

**Proposal.**
- **Don't deploy 6.5.2.** Wait for 6.5.3, or move to 7.x (T14).
- **On 6.5.1 now**, set `FC_fcrepo_ocfl_s3_timeout_connection_seconds` to something generous, for
  example 300, in the Fedora task's environment. In 6.5.1, and in 7.0.0, this property *is* the
  acquisition timeout.
- **Revisit at T14.** On any release with #2314, the same property becomes the TCP connect timeout,
  and the acquisition timeout becomes `fcrepo.ocfl.s3.timeout.acquisition.seconds` (#2327).
- **Optionally, raise `fcrepo.ocfl.s3.max_concurrency`.** Weigh that against S3 request rates and
  memory. Note that its name contains an underscore. According to its readme, our bootstrap container
  turns every `_` in an `FC_` variable into `.`, so this property needs either a bootstrap change or
  another way to pass it.

**Acceptance.**
- The setting is in all environments.
- A large-deposit commit on dev is no slower.
- No "Acquire operation took longer than the configured maximum time" errors in Fedora's logs.

### T5: Measure `fcrepo.ocfl.unsafe.write.enabled`

**Problem.** At commit, ocfl-java re-reads every staged byte to compute its digest, serially. Fedora
has already verified every binary against our `Digest` header at `PUT` time. Our importer then also
compares Fedora's recorded checksum with ours. The re-read is a third check of the same bytes, on local
disk, and it's on the critical path of every commit.

**Proposal.** On dev, time the large-deposit commit with and without
`FC_fcrepo_ocfl_unsafe_write_enabled=true`. With it on, ocfl-java trusts the digest it's given and skips
the re-read. Fedora's own warning: "If this value is incorrect, the object will be corrupted". The risk
is bytes changing on the staging disk between `PUT` and commit.

**Decide** whether the saving justifies dropping that check. An export with checksum verification
would still catch a bad file afterwards.

**Acceptance.** Commit-time figures with and without the setting, and a decision recorded here.

### T6: Record a commit in progress, and reconcile instead of reporting failure

**Problem.** If the importer dies during the commit `PUT` (a redeploy, a crash, an out-of-memory),
Fedora still finishes the commit (2.5). The heartbeat reaper then marks the job failed:
- the deposit goes to Error while the Archival Group has a new version;
- retrying a create fails, because the group now exists;
- retrying an update makes a confusing extra version.

#383 only covers failures the importer survives. On dev, every push to `main` redeploys the importer.

**Proposal.**
- Before the commit `PUT`, persist on the import job result: commit started, the transaction URI, the
  source version, and the time.
- When the reaper would mark such a job failed, or when an importer starts and finds one, resolve it
  the way #383 does instead:
  - wait for the transaction to finish, with a `GET` until 404 or 410;
  - then compare the Archival Group's OCFL version with the source version;
  - record Completed or CompletedWithErrors accordingly, with the evidence.
- Optionally, use the 410 body text ("already committed" versus "rolled back" or "expired") as a
  corroborating signal, but never as the only one.

**Acceptance.**
- Killing the importer mid-commit on dev leaves the job Completed once the commit lands, with the right
  new version, and the deposit is not in Error.
- Tests cover the reaper and startup paths.

### T7: Fewer requests per binary

**Problem.** Each binary takes a `PUT`, a `GET` of its description, possibly a title `PATCH`, and
another `GET`, then a client-side checksum comparison. That's two to four sequential requests per file.
Fedora already rejects a `PUT` whose content doesn't match the `Digest` header, so the comparison can't
fail on a successful `PUT`.

**Proposal.**
- Drop the post-`PUT` `GET` and checksum comparison.
- Set the title with one conditional SPARQL `PATCH`, an insert that only applies when there's no title.
- Read the description back only when the job result needs a field we don't already have.

Keep the error mapping and the tombstone handling.

**Acceptance.** Requests per binary go from 2–4 to 2. Import time for a many-file deposit on dev is
measurably lower, and the import tests are unchanged.

### T8: Run import jobs for different Archival Groups concurrently

**Problem.** One importer task runs one job at a time, so a long commit (tens of minutes) blocks every
other deposit's import.

**Proposal.** Allow N concurrent jobs, configurable, starting at 2 or 3, as long as each is for a
different Archival Group. Fedora's group-level lock already makes a clash a 409 rather than corruption,
and the Storage API already refuses to queue a second active job for the same group (`QueueImportJob`, 409).

Constraints:
- staging disk: the EBS volume is 1,000 GB, and must hold every in-flight import's payload;
- Fedora's database pool: a commit holds 2 connections for its duration, and each streaming `PUT`
  holds 1;
- task memory.

Do this after T6, since more concurrency makes reconciliation matter more.

**Acceptance.** Two imports for different groups overlap on dev, and a small import is no longer
blocked by a large one.

### T9: Runbook: an Archival Group wedged by a half-written version

**Problem.** If Fedora dies mid-upload, an orphan `vN/` prefix can be left in the OCFL bucket. The next
write to that object then fails with `ObjectOutOfSyncException`, so every import to that Archival Group
fails until the orphan is removed. Separately, a crash between the OCFL write and the database commit
leaves OCFL ahead of Fedora's index.

**Proposal.** Write the runbook in `docs/internals`:
- how to recognise each case from Fedora's logs and the import error;
- how to confirm the orphan against the root inventory's head version;
- how to remove it safely: the orphan prefix only, never a version the inventory lists;
- when `POST /{path}/fcr:reindex` or a restart is needed.

Rehearse the first case on dev.

**Acceptance.** The runbook exists and has been rehearsed once on dev.

### T10: Turn off Fedora debug logging in deployed environments

**Problem.** The Fedora task's `CATALINA_OPTS` sets `-Dfcrepo.log=DEBUG` in every environment.

**Proposal.** Make the log level a module variable. Default it to `INFO`, and use `DEBUG` only when
diagnosing.

**Acceptance.** Prod and test log at INFO, and log volume drops.

### T11: Spike: is there a stale containment cache after long commits?

**Problem.** *Inferred from source, untested:*
- Fedora invalidates its containment caches at the start of a commit
  ([`ContainmentIndexImpl`](https://github.com/fcrepo/fcrepo/blob/fcrepo-6.5.1/fcrepo-kernel-impl/src/main/java/org/fcrepo/kernel/impl/ContainmentIndexImpl.java),
  around L783-786).
- A non-transaction read during the upload could then cache "doesn't exist" for a new Archival Group.
- The caches are Caffeine with `expireAfterAccess` 10 minutes, so continued polling could keep it 404
  after the commit lands.

**Proposal.** On dev, start a large *new* Archival Group import. Poll `GET` on its path through the
Storage API every 30 s throughout the commit, and see whether it appears as soon as the commit returns.

**Acceptance.** Confirmed or ruled out. If confirmed, raise it upstream and decide on a mitigation
(not polling, or a shorter cache timeout via `fcrepo.cache.db.containment.timeout.minutes`).

### T12: Fedora fetches file bytes itself (spike first)

**Problem.** Every binary's bytes are relayed by the importer: it opens a stream from the deposit
object and sends it as the body of the `PUT` to Fedora (`FedoraClient.MakeBinaryPut`). The importer
therefore holds a long stream per binary, and before T1 that stream crosses the NAT gateway. The
TODO in `MakeBinaryPut` has wanted Fedora to fetch the bytes itself since the March 2024 prototype.

**What it would and wouldn't change.** For S3-origin binaries, this removes the importer's relay:
CPU, memory and one open stream per binary. It may also shorten the streaming phase of an import.
It doesn't change commit time, staging capacity, the one-transaction model, or the ALB idle cap on
each long request. And it adds a failure mode: a fetch that stalls inside Fedora. So it is worth
adopting only on measured evidence.

**What stops it on the Fedora we run.** On 6.5.1, and unchanged in 7.0.0, Fedora sends a `HEAD` to
any `http(s)` external-content URL before fetching it (`ExternalContentHandler.retrieveContentDetails`).
A non-200 fails the request. An S3 URL presigned for `GET` is signed for that method only, so the
`HEAD` gets a 403. Donald found this when he tried it in 2024. fcrepo #2331, merged on 2 September
2026 and not yet in a release, adds a `size` parameter to the Link header and skips the `HEAD` when
both `type` and `size` are given.

**The route.** On a Fedora containing #2331, `PUT` each binary with an empty body and:

```http
Link: <presigned GET URL>; rel="http://fedora.info/definitions/fcrepo#ExternalContent"; handling="copy"; type="<media type>"; size="<bytes>"
Digest: sha-256=<as now>
```

- **Size and type come from the deposit**, which already records both, so no `HEAD` is needed.
  - For `copy`, Fedora stores the byte count it actually staged, not the Link `size`, which only
    suppresses the `HEAD`.
  - The Link `type` *is* stored as the media type, so send the deposit's media type, as now.
  - The `Digest` header stays mandatory (`RequireDigestOnBinary`), and a copied stream goes through
    the same digest check as a streamed body.
- **Allow-list each deposit bucket in the exact host form the presigner emits.** Fedora's
  `fcrepo.external.content.allowed` check is a plain string prefix. The bootstrap already writes the
  file, but the current template (`files/allow_list.tftpl`) emits the global-endpoint form
  `https://<bucket>.s3.amazonaws.com/`, while a presigner configured for eu-west-1 most likely emits
  the regional `https://<bucket>.s3.eu-west-1.amazonaws.com/`. Replace the entry deployed today for
  the OCFL bucket (`s3-fedora.tf`), which is unused and left over from the 2024 prototype.
- **Presign just before each `PUT`, and never persist the URL.** S3 checks expiry when a request
  starts, so the URL only has to outlive the start of the fetch. A URL signed with role credentials
  also stops working when that role session ends.
- **Set JVM-wide timeouts for the fetch.** It uses `URL.openStream()`, which has no timeouts of its
  own, so add `-Dsun.net.client.defaultConnectTimeout` and `-Dsun.net.client.defaultReadTimeout` to
  the Fedora task's `CATALINA_OPTS`. Merge them into the existing string, which the ops module sets
  and which also carries `fcrepo.home`. Don't replace it.
- **Keep signed query strings out of logs and job results.** This is a hard requirement. Fedora logs
  the full source URL at DEBUG and puts it in exception messages. `FedoraClient` copies Fedora's
  error body into the import job's failure message, which reaches Preservation API callers. T10 turns
  DEBUG off, and the importer must scrub URLs from any Fedora error it records.
- **Choose per binary, with a fallback.** Streamed `PUT` stays available for anything without an S3
  origin. Don't retry a failed fetch by another route inside the same transaction: a failure during
  the fetch has already failed the transaction. A rejection before the fetch (allow-list mismatch,
  malformed Link) happens outside Fedora's transaction wrapper and leaves the transaction usable,
  but keep the rule simple and fail the job regardless.

**The bounded spike, on an isolated dev setup.** It doesn't need T1 or T14. RFC 010A defines the
full comparison; this is a delivery-and-capacity investigation, not just a check that the HTTPS
route works.
- **Image:** #2331 is on Fedora's `main`. The `7.1.0-SNAPSHOT` image was built on 24 September 2026,
  after the merge. Pin the image by digest and record it.
- **Data:** use a throwaway database and OCFL prefix, not the shared dev data. The snapshot bumps
  Flyway, and a later downgrade is unverified.
- **First check that the route works at all:**
  - the allow-list entry matches the presigned URL's host;
  - one `PUT` with `type` and `size` produces a `GET` and no `HEAD` at the source (the deposit buckets
    have S3 server access logging on);
  - a wrong digest is still rejected;
  - an expired URL and a missing object fail cleanly.
- **Compare** streamed `PUT`, HTTPS copy, and local-file copy; include a read-only S3-mount variant
  where practical. Use equivalent manifests with multiple deposit buckets, a file over 5 GB,
  many small files, and a realistic mixed deposit. Include source-preparation time and test a
  uniform fetch route as well as per-binary selection.
- **Measure** source preparation, binary staging and commit separately; record importer and Fedora
  CPU and memory, S3 requests, NAT bytes, ALB traffic, peak disk use, cleanup and operational cost.
- **Test failures and integrity:** source mutation, denied or expired access, interrupted and stalled
  reads, client cancellation, mount loss where applicable, and importer failure during fetch or
  commit. Verify recovery and reconciliation, and inspect logs and job results for signed URLs.
- **Control capacity:** use isolated, controlled storage limits and measure peak use and cleanup.
  Coordinated reservations must defer or reject work before writes begin before any route is
  adopted in production.
- **Agree the decision rule before the comparison:** what reduction would justify adopting it.

RFC 010A sets out the detailed procedure, including correctness checks and exit criteria.

**Adoption.** If the spike shows a gain worth the added failure mode, adopt it with the first release
that contains #2331. Ask upstream whether #2331 can be backported to `6.5-maintenance`, as #2327 was
(#2328). That would make it available without the 7.x upgrade.

**Not proposed:**
- **Patching our own Fedora build with #2331, or running a snapshot in production.** ADR 001's
  principle is a standard, unmodified Fedora. The change itself is small, but we'd be building,
  scanning and rebuilding our own image for every upstream release.
- **A mount as the default route or a production hosting change.**
  - Fedora's own storage would be untouched: a mount is only the source of a copy.
  - Mountpoint is FUSE, which Fargate can't run. A mount comparison may therefore require ECS on
    EC2, a hosting change that is not itself proposed for production.
  - It moves the same bytes, as S3 GETs behind a file-system daemon, and turns S3's error codes into
    generic I/O errors. Test its behaviour and failure recovery before treating it as equivalent to
    direct S3 access.
  - Multiple buckets may require additional mount configuration; the spike should test this against
    the external-applications goal in #410 rather than assume that buckets must be consolidated.
- **An interim on 6.5.1.** Unsigned S3 URLs plus a bucket policy allowing reads only through our
  gateway endpoint (`aws:SourceVpce`) would get past the `HEAD` today. But anything in the private
  subnets, including the pipeline hosts and every ECS task, could then read deposit objects without
  credentials. The Goobi bucket holds another organisation's content, so that exposure would need
  their agreement, not just ours. Only worth considering if a release is far off and the spike has
  shown a gain.

**Acceptance.**
- **Spike:** a written comparison and a recommendation against the agreed decision rule.
- **If adopted:**
  - binaries assigned to a direct-fetch or local-file route no longer stream through the importer;
  - mixed-route imports preserve target paths, metadata, digest verification and one version per import;
  - no signed URL appears in Fedora logs, importer logs or job results;
  - source bytes remain stable through reconciliation, and capacity is reserved before writes begin;
  - the TODO in `MakeBinaryPut` is replaced by the implementation.

### T13 (after T1): Simplify the transaction monitor

**Problem.** Once the commit request no longer crosses NAT, the monitor's 30-minute status check
guards against very little. Under T1's option (a) the ALB's 4,000 s idle cap remains, so #383's
outcome verification still matters for commits longer than that. As 2.6 shows, it's a second long request.

**Proposal.** Re-evaluate `FedoraTransactionMonitor`'s commit-started branch. Keep the pre-commit
keep-alive, which Fedora needs (2.3), and keep #383's outcome verification, which is cheap and
correct. Consider removing the commit-time poll and cancel, or lengthening it.

**Acceptance.** A decision, and code and `deployment.md` brought into line with it.

### T14: Upgrade Fedora to 7.x

**Problem.** Fedora 7 is the upstream line: fixes land on `main` first, and only some are
backported to 6.5.x. 7 also adds things we'd use:
- Prometheus metrics, including the database connection pool;
- faster reindexing;
- fewer database calls per `GET`/`HEAD`.

The release we pick matters for S3 (2.7, section 7):
- **7.0.0** behaves like 6.5.1. None of the post-6.5.1 S3 changes are in it, so it doesn't have
  6.5.2's 10-second acquisition timeout.
- **A 7.x released from current `main`** will have all of them, including the #2327 fix.
- **Avoid any build that has #2314 but not #2327.**

**Proposal.**
- Choose the release:
  - a 7.x release that includes #2327, if one exists when we start;
  - otherwise 7.0.0, keeping T4's setting.
- Then, on dev:
  - move the image to `fcrepo/fcrepo:<7.x>-tomcat10`, pinned by digest, keeping our bootstrap
    container and `FC_*` properties;
  - turn on `fcrepo.metrics.enabled` and scrape the metrics endpoint;
  - run the e2e suite, the large-deposit import (2,797 files, 38.7 GB) and a file over 5 GB;
  - check that our RDF parsing copes with 7's extra triples (`fedora:hasParent`, and membership and
    containment from inbound references) and deduplicated types;
  - confirm the health check still answers;
  - on a release with #2327, set `fcrepo.ocfl.s3.timeout.acquisition.seconds`, and turn T4's property
    back into what it now means, the TCP connect timeout.
- Then test, then prod.

Before prod, decide whether rolling back to 6.5.1 must be possible, and if so test it on dev. The
database change is additive, but a rollback is unverified.

**Acceptance.**
- 7.x on all environments, with e2e and the large-deposit test green.
- Metrics visible.
- Section 2's behaviour re-checked against the 7.x tag, and this RFC updated if anything moved.

## 7. Going straight to Fedora 7?

Fedora 7.0.0 was released on 16 April 2026, after alphas from December 2025 and an RC in March. Docker
images are published as `fcrepo/fcrepo:7.0.0-tomcat10`, along with `7-tomcat10` and a
`7.1.0-SNAPSHOT`. The 6.x line is still maintained on a `6.5-maintenance` branch, which produced 6.5.2
on 16 July 2026 by backporting from `main`.

### 7.1 What changes, and what doesn't

**The platform underneath changes:**
- Java 21;
- Servlet 6 and the Jakarta namespace, so Tomcat 10 or later (the image moves from `-tomcat9` to
  `-tomcat10`) or Jetty 12;
- Spring 6.2, up from 5.3.

**Transactions and storage don't change.** Between the 6.5.1 and 7.0.0 tags:
- `TransactionImpl`, `TransactionManagerImpl` and `Transactions` differ only cosmetically: Jakarta
  imports, and the clean-up task now logs, rather than throws, when it tries to roll back a committed
  transaction.
- fcrepo-storage-ocfl 7.0.0 has **no source changes** from 6.4.0, only build changes.
- ocfl-java is still **2.2.1**.

So **everything in section 2 applies equally to 7.0.0, and moving to 7 fixes none of P1–P10 by
itself.** The commit is still one synchronous request, staged files are still re-hashed and uploaded
at commit, and the locks and expiry work the same way.

**On S3, 7.0.0 behaves like 6.5.1.** All three post-6.5.1 S3 changes were merged to `main` *after*
the 7.0.0 tag:
- [fcrepo#2309](https://github.com/fcrepo/fcrepo/pull/2309), on 4 June 2026;
- [#2314](https://github.com/fcrepo/fcrepo/pull/2314), on 30 June;
- [#2327](https://github.com/fcrepo/fcrepo/pull/2327), on 24 August.

For us that's no loss. 7.0.0 doesn't have 6.5.2's fixed 10-second acquisition timeout (2.7), and
the multipart-copy fix is for a path we don't use. A 7.x released from current `main` will have all
three. `main` also has unreleased fixes for a delete and purge in the same transaction (FCREPO-4106),
and for ETags returned from `PATCH` and `PUT`.

**What 7 adds that we'd use:**
- **Metrics:** a Prometheus endpoint (`fcrepo.metrics.enabled`), including HikariCP pool metrics. That
  would show exactly the things T3, T5 and T8 have to reason about: database pool use during a commit,
  and request timings.
- **Faster reindexing** (FCREPO-4063). This matters for T9's recovery cases, and for any rebuild.
- **Fewer database calls per `GET`/`HEAD`** (FCREPO-4073). This helps the slow reads of very wide
  Archival Groups ([#244](https://github.com/digirati-co-uk/digital-preservation/issues/244)).
- **A current stack**, where upstream fixes land first.
- Also simple-search improvements and PREMIS 3 support, neither of which we depend on.

### 7.2 What it would touch in our code and configuration

Checked against our code:

| 7.x change | Effect on us |
|---|---|
| JSON-LD now defaults to the *expanded* form (fcrepo#2274) | None. `RequestX.ForJsonLd` always asks for the compacted profile explicitly |
| Deprecated `Content-Disposition` headers removed (FCREPO-4017) | None found. We don't read them, and our `WithContentDisposition` helper is unused |
| Extra triples: `fedora:hasParent`, and membership and containment from inbound references; RDF types deduplicated | Probably none: our converters read specific properties. The e2e suite and T14's checks should confirm it |
| Health check path `fcr:systeminfo` | Still present (`FedoraSystemInfo`) |
| Database schema | The PostgreSQL search script (`R__Create_search.sql`, a repeatable Flyway migration) only adds indexes. Nothing destructive in the diff |
| OCFL layout | Unchanged (same storage code), so **no data migration** |
| Our bootstrap container and `FC_*` properties | Should carry over: same property names, same `fcrepo.home` |

### 7.3 Maturity

The 7.x release-testing discussion
([fcrepo#2283](https://github.com/fcrepo/fcrepo/discussions/2283)) has three community reports, all
passes. Only one used S3 storage, with PostgreSQL. That's thin field experience for an S3-backed
deployment like ours.

The S3 code is also still settling. #2314 shipped a regression in 6.5.2 that #2327 fixed two months
later. Whatever we choose, run T14's large-deposit test before production.

### 7.4 Options

| Option | For | Against |
|---|---|---|
| **A. Stay on 6.5.1 with T4's setting, take 6.5.3 when it's released, and go to 7.x later** | The smallest change now | Three steps. No date for 6.5.3 |
| **B. 7.0.0 now, with T4's setting** | On 7 soonest. The same S3 behaviour as today. Metrics, faster reindexing and fewer database calls. No data migration | A platform change (Java 21, Tomcat 10) to test, which fixes none of P1–P10 by itself. A later 7.x update is still needed for #2327 |
| **C. Wait for a 7.x release that includes #2327, and do one upgrade** | One upgrade, onto the line with everything: #2327 for S3, and #2331, which T12 would need | No date. A `7.1.0-SNAPSHOT` image exists, but no release |
| **D. 6.5.2** | None for us | Not recommended: it cuts the small-file acquisition timeout to a fixed 10 s (2.7) |
| **E. Run a snapshot, or build from `main`** | Has everything | Not a release. Not for production |

**Proposed: go to 7, and skip 6.5.2.** Take C if a 7.x release with #2327 is out by the time T1–T3
are done; otherwise B. Either way, do T4's setting now. Take 6.5.3 (A) only if Fedora 7 work has to
wait a long time.

## 8. Decisions for Leeds and the team

- **D1. Keep one Fedora transaction per import** (section 3). Proposed: yes.
- **D2. Unsafe writes** (T5): accept skipping ocfl-java's commit-time re-hash, given the `PUT`-time
  digest check, if it makes a meaningful difference? Proposed: decide on the measurements.
- **D3. Private path to Fedora** (T1). Proposed: decide between (a), an internal ALB, which is about
  to be module-supported and is the pattern used for DLCS, but keeps the 4,000 s idle cap, and (b),
  service discovery, which is cap-free only as DNS-only Cloud Map or with Service Connect's timeouts
  set to 0. Take (a) unless measured commits approach an hour. Sub-decision: HTTP or HTTPS on the
  internal ALB.
- **D4. Import concurrency** (T8): how many concurrent imports? Proposed: start at 2.
- **D5. Fedora version path** (section 7, T4, T14): go straight to Fedora 7 and skip 6.5.2?
  Proposed: yes. Take a 7.x release that includes #2327 if one exists in time (any release cut from
  current `main` also has #2331, for T12; if upstream backports #2331 to 6.5-maintenance, a 6.5.3
  would serve T12 too), otherwise 7.0.0. Do
  T4's setting in the meantime.

## 9. What this paper has not verified

- **The Tomcat or connector request timeouts in the `6.5.1-tomcat9` image.** fcrepo itself never
  aborts a running commit. We haven't checked the container's configuration.
- **Whether `fcr:reindex` behaves well on an object that's already indexed.**
- **The stale containment cache in P10.** It's inferred from the code (T11).
- **Fedora's commit uses a `java.util.concurrent.Phaser` to wait for in-flight operations.** By JDK
  semantics, a Phaser with no parent terminates once its party count reaches zero, so that wait may
  only protect the first operation. We haven't tested it. Our importer never commits with a request
  still in flight, so it doesn't affect us.
- **How close the October commit test came to tripping the health check (T3).** That needs
  CloudWatch.
- **Whether ECS actually starts the second Fedora task during a deploy (T3).** We inferred it from
  the defaults, not observed it.
- **That the cost figures are current.** Check AWS pricing before using them in a business case.
- **The S3 upload paths** (2.7) are read from code. That files over 5 GB commit cleanly through the
  CRT transfer manager on 6.5.1 or 7.0.0, and that 6.5.2's 10-second acquisition timeout would hurt our
  many-file commits, are both inferences. Upstream's own report of the 6.5.2 regression supports the
  second.
- **Fedora 7** (section 7):
  - when a 7.x release with #2327, or 6.5.3, will appear;
  - whether rolling back from 7.x to 6.5.x works;
  - the exact Tomcat 10 build in the `-tomcat10` images;
  - whether our RDF converters cope with 7's extra triples. That's reasoned from our code, not tested.
  The source comparison covered the transaction, storage and configuration classes this RFC relies on,
  not every module.
- **T12 end to end.** That the `type` and `size` Link parameters suppress the `HEAD` is read from
  fcrepo `main` and its unit tests, not exercised against S3. The `7.1.0-SNAPSHOT` image was built
  after #2331 merged, but carries no commit label. The T12 spike is the test.
- **That the presigner's URL form matches the allow-list entry.** Fedora's check is a string prefix,
  and the template and the SDK's default host form may differ.
