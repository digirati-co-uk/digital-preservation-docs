# RFC 010: Fedora transaction improvements

**Status: draft for discussion.** This paper steps back from the run of fixes to how imports use
Fedora transactions ([#350](https://github.com/digirati-co-uk/digital-preservation/issues/350),
[#383](https://github.com/digirati-co-uk/digital-preservation/pull/383)) and asks whether the
approach is sound, and what should change around it. Its proposals are now issues under the epic
[#439](https://github.com/digirati-co-uk/digital-preservation/issues/439), which holds the working order. Section 6 lists them.

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
| [fcrepo#2327](https://github.com/fcrepo/fcrepo/pull/2327), backported as [#2328](https://github.com/fcrepo/fcrepo/pull/2328) | Restores a configurable acquisition timeout, `fcrepo.ocfl.s3.timeout.acquisition.seconds`, default 60. Upstream describes #2314's effect as a regression that users on 6.5.2 hit during commits under load | `main` (24 August 2026) and `6.5-maintenance` (9 October 2026). **Not yet released** (still so at 10 November 2026); it would be in a 6.5.3 |

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
| P3 | Fedora's ECS service uses default deployment settings | ECS defaults (minimum 100%, maximum 200%) run **two Fedoras** behind the ALB whenever the task is replaced: transactions live in one task's memory, and two tasks write OCFL at once. That happens on a deploy, and also about weekly with no deploy, when AWS retires the Fargate task for patching (seen in production on 9, 17 and 29 October 2026). The health check isn't a risk: it expects a `401`, which Tomcat answers before any Fedora code runs |
| P4 | Commit time scales with bytes, and includes a full local re-read | Long commits are the trigger for P1's timeouts, and they block the single importer (P7) |
| P5 | The S3 connection-pool acquisition timeout for files under 8 MB: 60 s on 6.5.1, a fixed 10 s on 6.5.2 | A commit with thousands of small files could fail waiting for a connection. Not observed on 6.5.1, since the October test passed, but 6.5.2 would make it more likely (2.7) |
| P6 | Importer death mid-commit is reported as a failure | Fedora finishes the commit, but the reaper marks the job failed. The deposit goes to Error while the Archival Group moved on, and a retry fails or makes a confusing extra version. Importer redeploys do this, and on dev every push to `main` redeploys it. So do AWS's task retirements, in production too (10 November 2026). #383 doesn't cover it |
| P7 | One importer runs jobs serially | A long import blocks every other deposit's import until it finishes |
| P8 | Two to four sequential HTTP requests per binary | Latency multiplied by thousands of files. The post-`PUT` checksum comparison is redundant, since Fedora already rejected a bad digest |
| P9 | Fedora runs with `-Dfcrepo.log=DEBUG` in every environment | Log volume, and some overhead, on every request |
| P10 | Possible stale cache for new resources after a long commit | *Inferred, untested.* Fedora invalidates its containment caches at the start of the commit, so a non-transaction read during the upload could cache "doesn't exist" for a new Archival Group, and keep returning 404 for up to 10 minutes after it lands while it keeps being polled. Our own outcome check reads the OCFL inventory from S3, so it isn't affected |

## 5. Proposals at a glance

| Id | Proposal | Repo | Size | Solves |
|---|---|---|---|---|
| T1 | Private network path from our services to Fedora | ops (+ platform config) | M | P1 |
| T2 | ~~S3 gateway VPC endpoint~~ Withdrawn: every environment already has one (section 1) | – | – | – |
| T3 | Run only one Fedora task at a time | ops | S | P3 |
| T4 | Skip Fedora 6.5.2, and widen the S3 acquisition timeout now | ops | XS | P5 |
| T5 | Evaluate `fcrepo.ocfl.unsafe.write.enabled` | ops (measure on dev) | S | P4 |
| T6 | Record a commit in progress, and reconcile instead of failing | platform | M | P6 |
| T7 | Fewer requests per binary | platform | S | P8 |
| T8 | Run import jobs for different Archival Groups concurrently | platform | M | P7 |
| T9 | Runbook: an Archival Group wedged by a half-written version | docs / ops | S | P3, 2.5 |
| T10 | Turn off Fedora debug logging in deployed environments | ops | XS | P9 |
| T11 | Spike: confirm or rule out the stale containment cache | platform | S | P10 |
| T12 | Spike, then possibly adopt: Fedora fetches file bytes itself (external content, `handling=copy`, presigned URL, needs fcrepo #2331) | platform + ops | M | P2 (partly) |
| T13 | Simplify the transaction monitor | platform | S | P1 follow-up |
| T14 | Upgrade Fedora to 7.x | ops + platform (test) | M | Section 7, P5 |

**Order.** The epic [#439](https://github.com/digirati-co-uk/digital-preservation/issues/439) holds the working order and owners. In outline:
1. **Alerts** for AWS task retirements and for two Fedoras running ([#464](https://github.com/digirati-co-uk/digital-preservation/issues/464)). They need no Fedora
   restart, and T3 depends on them.
2. **One Fedora change,** applied once with the importer idle: T3, T4 and T10. Each restarts Fedora.
3. **T9, then T6** with the commit-check fix ([#459](https://github.com/digirati-co-uk/digital-preservation/issues/459)); the atomic active-job check ([#460](https://github.com/digirati-co-uk/digital-preservation/issues/460))
   alongside.
4. **T1,** once D3 is taken; T5 measured on dev; T13.
5. **T14,** the move to Fedora 7 (section 7).
6. **Capacity admission** ([#461](https://github.com/digirati-co-uk/digital-preservation/issues/461)), then T8.
7. **T12:** first measure whether the importer is the constraint at all.

T7 and T11 fit in anywhere.

## 6. The proposals as issues

Each proposal is an issue in digital-preservation, under the epic [#439](https://github.com/digirati-co-uk/digital-preservation/issues/439). The issue is the working
text: what to do, and how to tell it's done. This section says what each is, and where review on 9 and
10 November 2026 changed the proposal as first drafted here.

| Id | Issue | Proposal | Changed after review |
|---|---|---|---|
| T1 | [#440](https://github.com/digirati-co-uk/digital-preservation/issues/440) | Reach Fedora on a private path, not through NAT and the internet-facing ALB. Proposed: an internal ALB, which the shared modules support from `v3.52` | The private hosted zone needs its own name; a second load balancer on Fedora's service restarts Fedora; the test is the ALB's access logs, since a large commit already returns its 204 with TCP keepalive |
| T2 | – | Withdrawn (below) | – |
| T3 | [#441](https://github.com/digirati-co-uk/digital-preservation/issues/441) | Minimum healthy 0%, maximum 100% on Fedora's service: stop-then-start, never two Fedoras | The health-check half is dropped (P3). AWS retirements make each replacement an outage at a time AWS chooses, so the alerts in [#464](https://github.com/digirati-co-uk/digital-preservation/issues/464) come first |
| T4 | [#442](https://github.com/digirati-co-uk/digital-preservation/issues/442) | Skip 6.5.2; set `fcrepo.ocfl.s3.timeout.connection.seconds` to 300 on 6.5.1 | The variable goes on the bootstrap container, the only one that reads `FC_*`. Pin the module's floating default image |
| T5 | [#443](https://github.com/digirati-co-uk/digital-preservation/issues/443) | Measure `fcrepo.ocfl.unsafe.write.enabled` on dev; decide D2 | Add a correctness check after the unsafe-write commit |
| T6 | [#444](https://github.com/digirati-co-uk/digital-preservation/issues/444) | Record a commit in progress, and reconcile instead of reporting failure | Both reap paths; no reconcile at importer start-up; persist the result lists before the commit; decide with a check that asks Fedora as well as S3 ([#459](https://github.com/digirati-co-uk/digital-preservation/issues/459)) |
| T7 | [#445](https://github.com/digirati-co-uk/digital-preservation/issues/445) | Two requests per new binary instead of four | The title `PATCH` also sets `createdBy`, so "is this new" must come from the job. Test the `PATCH` against a real Fedora |
| T8 | [#446](https://github.com/digirati-co-uk/digital-preservation/issues/446) | Import jobs for different Archival Groups run concurrently; decide D4 | Needs [#460](https://github.com/digirati-co-uk/digital-preservation/issues/460) and [#461](https://github.com/digirati-co-uk/digital-preservation/issues/461) first. Two creates under one parent may queue on a database row |
| T9 | [#447](https://github.com/digirati-co-uk/digital-preservation/issues/447) | Runbook for an Archival Group wedged by a half-written version | Three states, not one, with opposite repairs. Rehearsal needs a hard kill |
| T10 | [#448](https://github.com/digirati-co-uk/digital-preservation/issues/448) | Fedora logs at INFO in deployed environments | Fedora logs commit start and end only at DEBUG; keep those lines if the volume allows |
| T11 | [#449](https://github.com/digirati-co-uk/digital-preservation/issues/449) | Spike: is there a stale containment cache after a commit? | Applies to any new path, not only new Archival Groups |
| T12 | [#450](https://github.com/digirati-co-uk/digital-preservation/issues/450) | Fedora fetches file bytes itself (external content, `handling=copy`, presigned URL); see [RFC 010A](010A-ingress-file-management.md) | Measure first whether the importer is the constraint. The deployed allow-list entry can never match. Fedora logs the signed URL on any failed fetch |
| T13 | [#451](https://github.com/digirati-co-uk/digital-preservation/issues/451) | Simplify the transaction monitor's commit-time poll | Can be decided now; it doesn't depend on T1 |
| T14 | [#452](https://github.com/digirati-co-uk/digital-preservation/issues/452) | Upgrade Fedora to 7.x; decide D5 | A rehearsed rollback is part of acceptance. Proposed target is 7.0.0 (section 7.5) |

**T2, withdrawn.** This proposed an S3 gateway endpoint. Every environment already has one, created by
the shared VPC module (`terraform-aws-modules`, `tf/modules/vpc`, `public-private-igw/vpc_endpoints.tf`),
which isn't visible from preservation-ops alone. The id is kept so the other numbers don't change.

**Work the review added:**

| Issue | What |
|---|---|
| [#459](https://github.com/digirati-co-uk/digital-preservation/issues/459) | After an uncertain commit, confirm the outcome with Fedora as well as S3. If Fedora dies in the last moments of a commit, S3 can show a version Fedora doesn't have |
| [#460](https://github.com/digirati-co-uk/digital-preservation/issues/460) | Make the one-active-import-per-group check atomic, with a unique index |
| [#461](https://github.com/digirati-co-uk/digital-preservation/issues/461) | Capacity admission: reserve Fedora staging disk before an import writes |
| [#462](https://github.com/digirati-co-uk/digital-preservation/issues/462) | Decide how to protect or pin deposit sources during an import |
| [#463](https://github.com/digirati-co-uk/digital-preservation/issues/463) | Record the decisions in ADR 001 |
| [#464](https://github.com/digirati-co-uk/digital-preservation/issues/464) | Alerts: AWS task retirements, two Fedoras running, Fedora down, staging disk |
| [#465](https://github.com/digirati-co-uk/digital-preservation/issues/465) | The rollout and rollback plan for test and production |

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

**Proposed: B. Go to 7.0.0 now, keep T4's setting, and skip 6.5.2.** Take a later 7.x as an ordinary
upgrade when one is released. Section 7.5 says why waiting (C) isn't a plan. Take 6.5.3 (A) only if it
appears and Fedora 7 work has to wait a long time.

### 7.5 Upstream at 10 November 2026: is waiting for a later 7.x viable?

**Releases.** Nothing new since this section was written.
- The latest releases are still **7.0.0** (16 April 2026) and **6.5.2** (16 July 2026).
- **No 6.5.3.** The `6.5-maintenance` branch has had no commit since the [#2328](https://github.com/fcrepo/fcrepo/pull/2328) backport on
  9 October.
- [#2327](https://github.com/fcrepo/fcrepo/pull/2327) and [#2331](https://github.com/fcrepo/fcrepo/pull/2331) are merged to `main` and in no release. Nobody has proposed backporting
  #2331 to 6.5.
- The only build with both is the `7.1.0-SNAPSHOT` Docker image, last rebuilt on 6 November. It is a
  moving tag, not a release.
- We found no announced date for a 7.1 or a 6.5.3.

**`main` has moved a long way from 7.0.0.** Beyond the S3 and external-content changes above, since
late October it has taken:
- a 70-dependency update ([#2358](https://github.com/fcrepo/fcrepo/pull/2358)), Grizzly 5 ([#2345](https://github.com/fcrepo/fcrepo/pull/2345)) and Flyway 13 (7.0.0 has 11.20.3);
- Artemis support for messaging ([#2306](https://github.com/fcrepo/fcrepo/pull/2306));
- ocfl-java 2.2.3, up from 2.2.1 (its release notes list dependency updates only);
- a fix for a race when resources with the same new RDF type are created concurrently ([#2352](https://github.com/fcrepo/fcrepo/pull/2352));
- a fix for a containment index that isn't created on PostgreSQL 16 or later ([#2357](https://github.com/fcrepo/fcrepo/pull/2357)). Our
  production database is PostgreSQL 14, so that matters to us only at the next major database upgrade.

Jersey 4 and HikariCP 7 updates are open.

**So, is waiting viable?** As a plan, no:
- **There is no date to wait for.**
- **The next 7.x won't be "7.0.0 plus two fixes".** It will be a larger change than 7.0.0 was from
  6.5.1 in the areas we depend on, and will need the full T14 test whenever we take it. Going to 7.0.0
  first doesn't add an upgrade we could otherwise avoid; it splits one large step into two smaller ones.
- **Nothing in steps 1 to 4 of the order depends on a Fedora release.** They are our own configuration
  and code.
- **We can live without #2327 on 7.0.0.** Like 6.5.1, 7.0.0 has neither #2314 nor #2327, so T4's
  setting works there unchanged.
- **Only adopting T12 needs a future release,** for #2331. T12 is gated on measurements that may end it
  anyway, and its spike can use a pinned snapshot.

What to watch for: a 7.1 or 6.5.3 release announcement. When one appears, check that it carries #2327
before considering it, and never run a build with #2314 and without #2327.

## 8. Decisions for Leeds and the team

- **D1. Keep one Fedora transaction per import** (section 3). Proposed: yes.
- **D2. Unsafe writes** (T5): accept skipping ocfl-java's commit-time re-hash, given the `PUT`-time
  digest check, if it makes a meaningful difference? Proposed: decide on the measurements.
- **D3. Private path to Fedora** (T1). Proposed: (a), an internal ALB, which the shared modules support
  from `v3.52` and is the pattern used for DLCS, but keeps the 4,000 s idle cap. The alternative is (b),
  service discovery, which is cap-free only as DNS-only Cloud Map or with Service Connect's timeouts
  set to 0. Take (a) unless measured commits approach an hour. Sub-decision: HTTP or HTTPS on the
  internal ALB.
- **D4. Import concurrency** (T8): how many concurrent imports? Proposed: start at 2.
- **D5. Fedora version path** (section 7, T4, T14): go to Fedora 7 and skip 6.5.2? Proposed: yes, to
  7.0.0 now, with T4's setting, and a later 7.x as an ordinary upgrade when one is released
  (section 7.5). Adopting T12 needs a release with #2331.

## 9. What this paper has not verified

- **The Tomcat or connector request timeouts in the `6.5.1-tomcat9` image.** fcrepo itself never
  aborts a running commit. We haven't checked the container's configuration.
- **Whether `fcr:reindex` behaves well on an object that's already indexed.**
- **The stale containment cache in P10.** It's inferred from the code (T11).
- **Fedora's commit uses a `java.util.concurrent.Phaser` to wait for in-flight operations.** By JDK
  semantics, a Phaser with no parent terminates once its party count reaches zero, so that wait may
  only protect the first operation. We haven't tested it. Our importer never commits with a request
  still in flight, so it doesn't affect us.
- **How long Fedora is unavailable when its task is replaced stop-then-start (T3).** Each new task
  gets a new EBS volume. Measure it on dev.
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
  fcrepo `main` and its unit tests, not exercised against S3. The `7.1.0-SNAPSHOT` image is rebuilt
  as `main` moves (last on 6 November 2026) and carries no commit label. The T12 spike is the test.
- **That the presigner's URL form matches the allow-list entry.** Fedora's check is a string prefix,
  and the template and the SDK's default host form may differ.
- **The commit-check gaps in digital-preservation#459.** That S3 can show a version Fedora doesn't
  have, and what the platform then records, are read from ocfl-java's and our own source, not
  reproduced.
