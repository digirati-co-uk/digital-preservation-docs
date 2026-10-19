# RFC 010: Fedora transaction improvements

**Status: draft for discussion.** This paper steps back from the run of fixes to how imports use
Fedora transactions ([#350](https://github.com/digirati-co-uk/digital-preservation/issues/350),
[#383](https://github.com/digirati-co-uk/digital-preservation/pull/383)) and asks whether the
approach is sound, and what should change around it. It is written to be turned into issues on the
backlog board. Section 6 has indicative issue text for each proposal.

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

Links go to those tags. Where something is inferred rather than read in the code, it says so. Section 8
lists what we haven't verified.

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
- **There is no S3 gateway VPC endpoint** in any environment. So both the importer's reads from the
  deposit bucket and Fedora's writes to the OCFL bucket also go through the NAT gateway.
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

### 2.7 Known problems in 6.5.1, fixed in 6.5.2

Fedora 6.5.2 was tagged on 2026-07-15
([fcrepo#2319](https://github.com/fcrepo/fcrepo/pull/2319)). Relevant fixes:

- **[FCREPO-4084](https://github.com/fcrepo/fcrepo/pull/2309), "Ocfl java s3 5gb issue".**
  `fcrepo.ocfl.s3.timeout.connection.seconds`, default 60, was wired to the *connection-pool
  acquisition* timeout. So the parts of a multipart upload, or thousands of small files queued behind
  the 100 S3 connections, could time out waiting for a connection and fail the commit. 6.5.2 makes it
  a TCP connect timeout ([fcrepo#2314](https://github.com/fcrepo/fcrepo/pull/2314)).
  - **This bears directly on [RFC 009](009-large-files.md):** a file over 5 GB may fail at commit on
    6.5.1 for this reason alone.
  - It may also matter for very wide Archival Groups ([#244](https://github.com/digirati-co-uk/digital-preservation/issues/244)).
- **An AWS SDK upgrade.**

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

One variant *is* worth having later: **external content with `handling=copy` and a presigned HTTPS S3
URL**. Fedora fetches the bytes itself at `PUT` time, then stages and commits them exactly as now, so
nothing about the model changes. It's the TODO already in `FedoraClient.MakeBinaryPut`. See T12.

## 4. Where it hurts

| # | Problem | Effect |
|---|---|---|
| P1 | Service traffic to Fedora goes out through NAT to an internet-facing ALB and back | The 350 s NAT idle drop and the 4,000 s ALB cap. Most of #350 and #383 exists to survive this. Fedora is also on an internet-facing load balancer when only our own services need it |
| P2 | No S3 gateway endpoint | Every ingested byte crosses the NAT gateway about three times: importer reads the deposit, importer sends to Fedora, Fedora uploads at commit. NAT data processing is charged per GB, about $0.05 in eu-west-1 at the time of writing, and it's another hop to fail |
| P3 | Fedora's ECS service uses default deployment settings and a strict health check | ECS defaults (minimum 100%, maximum 200%) should briefly run **two Fedoras** behind the ALB during a deploy: transactions live in one task's memory, and two tasks would write OCFL at once. The health check has a 10 s timeout and marks the task unhealthy after 2 failures 30 s apart. A slow health endpoint during a heavy commit could get Fedora replaced mid-commit, which is the "wedged Archival Group" case in 2.5 |
| P4 | Commit time scales with bytes, and includes a full local re-read | Long commits are the trigger for P1's timeouts, and they block the single importer (P7) |
| P5 | Fedora 6.5.1's S3 connection-pool timeout bug | Large files, and possibly very many files, can fail at commit (2.7) |
| P6 | Importer death mid-commit is reported as a failure | Fedora finishes the commit, but the reaper marks the job failed. The deposit goes to Error while the Archival Group moved on, and a retry fails or makes a confusing extra version. Importer redeploys do this, and on dev every push to `main` redeploys it. #383 doesn't cover it |
| P7 | One importer runs jobs serially | A long import blocks every other deposit's import until it finishes |
| P8 | Two to four sequential HTTP requests per binary | Latency multiplied by thousands of files. The post-`PUT` checksum comparison is redundant, since Fedora already rejected a bad digest |
| P9 | Fedora runs with `-Dfcrepo.log=DEBUG` in every environment | Log volume, and some overhead, on every request |
| P10 | Possible stale cache for new resources after a long commit | *Inferred, untested.* Fedora invalidates its containment caches at the start of the commit, so a non-transaction read during the upload could cache "doesn't exist" for a new Archival Group, and keep returning 404 for up to 10 minutes after it lands while it keeps being polled. Our own outcome check reads the OCFL inventory from S3, so it isn't affected |

## 5. Proposals at a glance

| Id | Proposal | Repo | Size | Solves |
|---|---|---|---|---|
| T1 | Private network path from our services to Fedora | ops (+ platform config) | M | P1 |
| T2 | S3 gateway VPC endpoint | ops | S | P2 |
| T3 | Fedora ECS deployment and health-check settings | ops | S | P3 |
| T4 | Upgrade Fedora to 6.5.2 | ops | S–M | P5 |
| T5 | Evaluate `fcrepo.ocfl.unsafe.write.enabled` | ops (measure on dev) | S | P4 |
| T6 | Record a commit in progress, and reconcile instead of failing | platform | M | P6 |
| T7 | Fewer requests per binary | platform | S | P8 |
| T8 | Run import jobs for different Archival Groups concurrently | platform | M | P7 |
| T9 | Runbook: an Archival Group wedged by a half-written version | docs / ops | S | P3, 2.5 |
| T10 | Turn off Fedora debug logging in deployed environments | ops | XS | P9 |
| T11 | Spike: confirm or rule out the stale containment cache | platform | S | P10 |
| T12 | Later: Fedora fetches file bytes itself (`handling=copy`, presigned URL) | platform + ops | M | P2, P4 (partly) |
| T13 | After T1: simplify the transaction monitor | platform | S | P1 follow-up |

**Suggested order:**
1. **First:** T3 and T10, which are configuration only and remove a real risk; T2, cheap; and T11, a
   quick check.
2. **Then:** T1, the change that removes the timeouts at their root; and T4 with T5, measured together
   on dev with a large deposit.
3. **Then:** T6, before T8 (concurrency makes reconciliation more important), and T7 any time.
4. **Later:** T9 alongside T3, and T12 and T13 once T1 has landed.

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
- (b) **ECS Service Connect or Cloud Map service discovery** straight to the Fedora task: no load
  balancer, so no idle cap. Fedora is a single task, so there's nothing to balance.

Point the importer's and Storage API's `Fedora__Root` at it. Decide whether anything still needs
Fedora on the public ALB, such as admin access, and if not, remove the listener rule.

**Check before switching.** Fedora builds resource URIs from the request's host. Confirm that nothing
we persist holds full Fedora URLs: not the Storage or Preservation API databases, not the import job
JSON, not METS. Confirm too that the Storage API's URI conversion only depends on `Fedora__Root`.
Change both services in the same deploy.

**Acceptance.**
- No Fedora traffic from our services crosses the NAT gateway.
- On dev, a commit longer than 70 minutes returns its 204 directly, with option (b).
- `deployment.md`'s "Reaching Fedora" section is rewritten.
- TCP keepalive (120/30/5) stays, as dead-peer detection.

### T2: Add an S3 gateway VPC endpoint

**Problem.** No environment has an S3 gateway endpoint. The importer's reads of deposit files,
Fedora's commit uploads, the pipeline's S3 access and the Preservation API's S3 calls all go through
the NAT gateway. That costs data processing per GB, and the NAT is another hop to fail.

**Proposal.** Add a gateway endpoint for S3 (`com.amazonaws.<region>.s3`) to each VPC's private route
tables. Gateway endpoints are free. Check any bucket policies that rely on a source IP. With an
endpoint, requests arrive from the VPC, not the NAT's address, so use `aws:sourceVpce` or `aws:SourceVpc`
conditions if needed.

**Acceptance.**
- S3 traffic from private subnets uses the endpoint, visible in route tables and NAT byte metrics.
- No access regressions on dev, then test, then prod.

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

### T4: Upgrade Fedora to 6.5.2

**Problem.** In 6.5.1, `fcrepo.ocfl.s3.timeout.connection.seconds` (60 s) is the S3 connection-pool
*acquisition* timeout. Multipart parts of a large file, or thousands of small files queued behind the
100 S3 connections, can wait longer than that and fail the commit. That's
[FCREPO-4084](https://github.com/fcrepo/fcrepo/pull/2309), "Ocfl java s3 5gb issue", fixed in 6.5.2
([fcrepo#2314](https://github.com/fcrepo/fcrepo/pull/2314),
[fcrepo#2319](https://github.com/fcrepo/fcrepo/pull/2319)). RFC 009's files over 5 GB depend on it.

**Proposal.**
- Move the Fedora image to `fcrepo/fcrepo:6.5.2-tomcat9`, pinned by digest, on dev.
- Read the 6.5.2 release notes for any migration steps.
- Run the e2e suite and a large-deposit import: the 2,797-file, 38.7 GB test set, plus at least one
  file over 5 GB.
- Then test, then prod. Measure alongside T5.

**Acceptance.** 6.5.2 is on all environments, e2e is green, and a file over 5 GB imports on dev. Feed
the result back into RFC 009.

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

### T12 (later): Fedora fetches file bytes itself

**Problem.** File bytes travel S3, then the importer, then Fedora. The importer hop adds latency,
memory and, before T1 and T2, NAT traffic.

**Proposal.** `PUT` each binary as external content with `handling=copy` and a short-lived presigned
HTTPS URL for the deposit object. Fedora fetches at `PUT` time, then stages, verifies and commits
exactly as now. Notes:
- `s3://` URIs aren't supported, but HTTPS is;
- the URL must prefix-match Fedora's `fcrepo.external.content.allowed` file, which the bootstrap
  already supports;
- presigned URLs must outlive the fetch.

This resolves the TODO in `FedoraClient.MakeBinaryPut`.

**Acceptance.** Imports on dev no longer stream bytes through the importer, and digest verification is
unchanged.

### T13 (after T1): Simplify the transaction monitor

**Problem.** Once the commit request no longer crosses NAT or an ALB idle cap, the monitor's
30-minute status check guards against very little. As 2.6 shows, it's a second long request.

**Proposal.** Re-evaluate `FedoraTransactionMonitor`'s commit-started branch. Keep the pre-commit
keep-alive, which Fedora needs (2.3), and keep #383's outcome verification, which is cheap and
correct. Consider removing the commit-time poll and cancel, or lengthening it.

**Acceptance.** A decision, and code and `deployment.md` brought into line with it.

## 7. Decisions for Leeds and the team

- **D1. Keep one Fedora transaction per import** (section 3). Proposed: yes.
- **D2. Unsafe writes** (T5): accept skipping ocfl-java's commit-time re-hash, given the `PUT`-time
  digest check, if it makes a meaningful difference? Proposed: decide on the measurements.
- **D3. Private path to Fedora** (T1): option (b), no load balancer, so no idle cap? Proposed: yes,
  unless something still needs Fedora on the public ALB.
- **D4. Import concurrency** (T8): how many concurrent imports? Proposed: start at 2.

## 8. What this paper has not verified

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
