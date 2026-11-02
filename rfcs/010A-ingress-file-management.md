# RFC 010A: Ingress file management  
 
**Status: draft for discussion and a bounded spike.** A counterpoint to
[RFC 010: Fedora transaction improvements](010-fedora-transaction-improvements.md),
particularly T12, which leaves Fedora fetching its own content until later.

**Proposal:** investigate file delivery as an architectural concern now, not just a later
optimisation. Separate the importer's control of an import from the movement of its bytes.
Test a mixed model in which individual files can be streamed, fetched from S3, or read from
a filesystem visible to Fedora, while retaining one transaction per import.

This does not propose abandoning RFC 010's transaction model, private networking, or commit
reconciliation. It challenges whether improving the existing streaming path is enough.
It is not a claim that a filesystem mount makes Fedora commits asynchronous or removes staging.

## 1. The question RFC 010 leaves open

The importer currently reads each binary from its origin and streams it into a Fedora request.
This is visible in
[`FedoraClient.MakeBinaryPut`](https://github.com/digirati-co-uk/digital-preservation/blob/main/src/DigitalPreservation/Storage.API/Fedora/FedoraClient.cs):
it obtains a storage stream, wraps it in `StreamContent`, and attaches the expected digest.
The same method already has a TODO about letting Fedora fetch the content instead.

For large deposits, the importer is therefore both an orchestrator and a bulk-data relay.
Changing network routes improves that relay, but does not remove it.

The pipeline container already makes deposit S3 content available for ClamAV
and other processing. That is a reason to investigate reuse, not evidence that Fedora can
already see those files. The spike must establish whether this is an S3 mount, a downloaded
workspace, or another access mechanism, and how long those bytes remain available.

Supporting multiple deposit S3 buckets for external applications is a goal. The ingress design and spike should account for that goal rather than assume a single deposit bucket.

Multiple deposit S3 buckets add a source-access question: can Fedora fetch directly from each
bucket, or would some content benefit from a shared ingress workspace? The spike should compare
direct access with selective staging to local disk or a dedicated S3 staging bucket.
Multiple buckets do not inherently require consolidation: per-object signed URLs can address
different buckets, while mounts may require additional configuration. Additional staging should
have a demonstrated benefit, since it introduces another copy, storage or capacity costs, and
cleanup responsibilities.

AWS data transfer timing and costing should be a consideration. 

The hypothesis is:

> Letting Fedora read source bytes directly can reduce importer involvement, bulk traffic
> through the Fedora-facing API path, and transfer-related failures. Existing file-processing
> arrangements may make local-file delivery practical as well as HTTPS delivery.

These benefits need measurement. A mount is not inherently more reliable than HTTP, and
moving a transfer does not eliminate it.

## 2. Two waits, not one

| Phase | Work | Effect of changing the source-delivery route |
|---|---|---|
| Binary request | Receive or fetch the binary, verify it, and stage it locally | Removes the importer relay for fetched content, but the request still waits |
| Transaction commit | Prepare the OCFL update, including digest work and uploads to the preservation bucket | Still synchronous; no demonstrated reduction from changing the source route alone |

RFC 010 reports a 22-minute commit after staging a 38.7 GB deposit. That is distinct from
the time spent delivering the files to Fedora.

An external-content request is not an asynchronous instruction to fetch later. It can still
be a long request through an ALB, even when its request body is small. Transaction keep-alives,
the private Fedora route, and reconciliation after an uncertain commit remain necessary.

## 3. Supported building blocks

Fedora 7.0.0's
[`ExternalContentHandler`](https://github.com/fcrepo/fcrepo/blob/fcrepo-7.0.0/fcrepo-http-api/src/main/java/org/fcrepo/http/api/ExternalContentHandler.java)
reads `file:`, `http:` and `https:` sources. With external-content `handling=copy`, source
bytes are copied into Fedora's managed content rather than retained only as a reference.
This is the relevant mode: proxy or redirect would not preserve the bytes in OCFL.

The source must pass Fedora's
[`ExternalContentPathValidator`](https://github.com/fcrepo/fcrepo/blob/fcrepo-7.0.0/fcrepo-http-api/src/main/java/org/fcrepo/http/api/ExternalContentPathValidator.java)
and the configured `fcrepo.external.content.allowed` list. A source path must be readable
inside the Fedora container; a path in another container is not sufficient.

**HTTPS compatibility needs an early test.** In 7.0.0, the handler sends an HTTP `HEAD` to
obtain source details and then opens the source URL to read its content. An S3 URL presigned
for `GET` is method-specific: do not assume that the same URL authorises `HEAD`. Prove a
working authenticated delivery mechanism before adopting RFC 010 T12's presigned-URL approach.
Any required adapter or Fedora change for that release is part of the cost of that option,
not a hidden assumption.

Both `fcrepo.ocfl.staging` and `fcrepo.ocfl.temp` remain supported in
[`OcflPropsConfig`](https://github.com/fcrepo/fcrepo/blob/fcrepo-7.0.0/fcrepo-configs/src/main/java/org/fcrepo/config/OcflPropsConfig.java).
Their wiring is in
[`OcflPersistenceConfig`](https://github.com/fcrepo/fcrepo/blob/fcrepo-7.0.0/fcrepo-persistence-ocfl/src/main/java/org/fcrepo/persistence/ocfl/impl/OcflPersistenceConfig.java).
In storage library 7.0.0,
[`DefaultOcflObjectSession`](https://github.com/fcrepo-exts/fcrepo-storage-ocfl/blob/7.0.0/src/main/java/org/fcrepo/storage/ocfl/DefaultOcflObjectSession.java)
still stages resource content locally before the OCFL commit.

These are source-supported mechanisms, not a verified end-to-end platform implementation.
Test the exact deployed Fedora version as well as any proposed 7.x upgrade.

### 3.1 Local source check: a practical path on 7.1.0-SNAPSHOT

On 22 October 2026, we checked the local Fedora clone at **7.1.0-SNAPSHOT,
commit `c2d13bdf89`, 26 commits after 7.0.0, not the released 7.0.0 source**.
The full commit is
[`c2d13bdf89cad2f3e863a5078714610dd45db2b5`](https://github.com/fcrepo/fcrepo/commit/c2d13bdf89cad2f3e863a5078714610dd45db2b5).
It still depends on fcrepo-storage-ocfl 7.0.0 and ocfl-java 2.2.1.
These findings apply to that snapshot; do not assume a `7.0.0` image contains its changes.

The important difference is in
[`ExternalContentHandler`](https://github.com/fcrepo/fcrepo/blob/c2d13bdf89cad2f3e863a5078714610dd45db2b5/fcrepo-http-api/src/main/java/org/fcrepo/http/api/ExternalContentHandler.java):
when the external-content Link supplies **both `type` and a valid, non-negative `size`**,
the handler skips metadata discovery and therefore makes no preliminary HTTP `HEAD`.
If either is missing, it still attempts `HEAD` for an HTTP/HTTPS source.

This gives the spike a concrete first test: use an S3 GET-presigned URL and provide both
values from the verified source manifest. For example, on the snapshot:

```http
PUT /archive/group/image.tif
Link: <https://deposit-bucket.example/image.tif?SIGNED_QUERY>; rel="http://fedora.info/definitions/fcrepo#ExternalContent"; handling="copy"; type="image/tiff"; size="123456789"
```

Also send the usual transaction and expected `Digest` headers. The hostname, query and size
above are placeholders, not a usable signed request. `type` and `size` are parameters of the
**Link header**, not the content length of the empty API request body.
Supplying `size` avoids discovery; it is not a substitute for digest verification or proof
that the fetched body has that length.

Verify that the source receives `GET` but no `HEAD`, then repeat with either parameter omitted
to demonstrate the version-specific behaviour. Test the real signed S3 URL, allow-list,
expiry and digest handling end to end before treating this as a supported platform route.
This may avoid an HTTPS adapter, but it does not justify deploying a snapshot to production:
choose a release containing the change, or separately evaluate maintaining a backport.

The code trace also confirmed:

- Both create and replace operations fetch `handling=copy` content into the internal-binary
  persistence path. Delivery is selected per request, not per transaction, supporting the mixed
  model without introducing a different preservation format.
- The internal-binary path computes and checks supplied digests while staging the fetched stream.
  Existing integration-test source covers local/HTTP copy and wrong-digest rejection.
- The resolved storage library copies the stream into local staging. Reading a local file
  does not adopt it in place. Commit still waits for the OCFL object-session commits.
- HTTPS fetching uses Java `URL.openStream()`, not the AWS SDK. That fetch method configures
  no explicit connect/read timeouts or retry policy; do not assume AWS SDK resilience.
- Fedora can log complete source URLs at DEBUG and include them in exception messages.
  Signed-URL query strings therefore need protection in logs and propagated errors, not just
  in the importer's persisted delivery plan.

**Validation performed:** the handler, handler-factory and path-validator unit-test classes
built successfully: 34 tests passed, one skipped, no failures. This was not an S3 or mount
test. Integration tests, mixed deposits, large files, capacity exhaustion and restart recovery
remain part of the spike, not established outcomes.

## 4. Delivery options

| Route | Benefit | Cost or constraint |
|---|---|---|
| Existing streamed `PUT` | Baseline; no new source access from Fedora | Importer relays every byte |
| HTTPS source with `handling=copy` | Fedora reads deposit content without an importer relay; potentially retains current hosting | On 7.0.0, authenticate both `HEAD` and content reads; on the checked snapshot, supply Link `type` and `size` to skip `HEAD`. Verify expiry and source access |
| Local file with `handling=copy` | Can reuse bytes already materialised for processing | Requires a shared, stable source visible to Fedora; may add a separate download and disk copy |
| Read-only S3 mount exposed as local files | Fedora uses local-file access without pre-downloading the whole deposit | Requires mount lifecycle, credentials and filesystem semantics to be managed |

For the mount option, evaluate ECS on EC2 with a host mount exposed read-only to Fedora.
This is an option to test, not a decision to migrate hosting. Include host maintenance,
task placement, remounting and failure recovery in the comparison.

[Mountpoint for Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mountpoint.html)
translates filesystem operations into S3 calls and does not provide a complete POSIX filesystem.
Use it only as a candidate source of deposit files, not as Fedora's staging or temp filesystem,
and not as a substitute for Fedora's native OCFL S3 backend.

An S3 gateway endpoint is a separate concern. Neither mounting a bucket nor using HTTPS by itself
proves that S3 traffic bypasses NAT. Verify the actual route. Private Fedora connectivity is
also separate: smaller control requests do not remove the ALB's idle timeout.

Infrastructure implementation and authoritative configuration belong in
[preservation-ops](https://github.com/uol-dlip/preservation-ops); this RFC does not prescribe
environment-specific paths, bucket names or capacities.

## 5. Mixed deposits, one import

Choose delivery per binary, not per deposit. A deposit may contain small metadata files,
large images and video, and processing outputs with different source availability.
All routes must preserve the same logical target paths, metadata, digests and transaction:

```text
One import job / one Fedora transaction
  metadata.xml   -> streamed PUT
  image.tif      -> HTTPS copy from deposit S3
  video.mov      -> HTTPS copy or read-only mounted source
  processed.bin  -> local-file copy, if available to Fedora
One commit / one OCFL version
```

This is an illustrative policy, not a proposed fixed size threshold.
The importer should:

- Build a per-file delivery plan from source identity, size, digest and availability.
- Reuse existing deposit S3 objects instead of creating another staging bucket without a reason.
- Consider both per-file size and aggregate deposit size; many small files can exhaust disk too.
- Select a tested route before issuing the binary request, recording the route without credentials.
- Keep callers independent of physical delivery choices.
- Preserve existing metadata, tombstone handling and error reporting across routes.
- Apply the same fixity requirements to copied and streamed bytes, including negative tests.

Source bytes must remain stable from verification through delivery. Establish a source immutability
or version-pinning mechanism, and retain the source until import reconciliation is complete.
Generate expiring access just before use; do not persist credentials or signed URLs in job results.
Inspect Fedora and importer logs and failed-job output for signed URLs. Establish query-string
redaction before production use; lowering logging verbosity alone does not address exception
messages.
Constrain filesystem paths to the approved workspace and expose source mounts read-only.

Do not silently retry a failed binary through another route in the same transaction:
the failure may already have made that transaction unusable. Determine transaction state and
perform explicit recovery. An uncertain commit must be reconciled before replaying the import.

Also test fetching all S3-resident files, not only large ones. If that works well for small files,
a uniform fetch route may be simpler than a size-based hybrid.

## 6. Capacity is still an admission constraint

Source staging and Fedora staging are different allocations. Fedora's copy operation does not
adopt an existing source file in place or bypass its staging directory.

For production, before opening a transaction, estimate the bytes that will be staged and reserve
capacity against other admitted imports. Account for temporary work, metadata, any separately
materialised source workspace on the same volume, and measured operational headroom.
Do not use only the largest file or uncoordinated free-space snapshots as the admission check.

Both Fedora directories must be on the intended disk. If they are on an attached EBS filesystem,
that filesystem's free space is the relevant limit, not Fargate ephemeral capacity.
Configuration values alone do not prove that the mount is present.

The spike should use controlled capacity, measure peak usage and cleanup after failure, and
derive admission requirements. It does not require building a production reservation system
as part of the delivery comparison. Any deliberate disk-exhaustion test must use an isolated
test environment, not a shared filesystem.

Before production adoption, implement and test coordinated capacity reservations. Admission
must defer or explicitly reject work when capacity cannot be reserved; it must not discover
the limit by filling the filesystem halfway through an import.

Keep commit-time digest verification enabled for the comparison. Changing it at the same time
would confound the measurements and introduce a separate integrity decision.

## 7. Bounded spike

### Preparation

1. Establish how the existing scanning container accesses deposit bytes and whether those
   exact bytes can safely be reused. Do not bypass required processing or scan acceptance.
2. Prove a single authenticated HTTPS copy and a local-file copy on the exact Fedora image.
   For 7.0.0, account for `HEAD`; for the snapshot described in section 3.1, verify that Link
   `type` and `size` suppress it. Verify allowed paths and wrong-digest rejection.
3. Record hosting, network route, storage, Fedora version and configuration for every run.
   Compare delivery routes under equivalent conditions; measure network changes separately.
4. Include test sources from multiple deposit buckets to exercise this work round's development
   goal for external applications. Establish the access and allow-list requirements for each
   route without assuming that all content must first be copied into one bucket or that
   production multi-bucket support already exists.

### Comparison

Run the existing streaming baseline, HTTPS fetching, and local-file delivery with identical
input manifests. Include a read-only S3-mount variant where practical; explicitly distinguish
mount-on-demand from pre-downloading a workspace.
Where selective staging to a dedicated S3 bucket is proposed, include source-to-staging copy
time, fixity checks, retention, cleanup and storage costs in the comparison.

Use a many-small-file deposit, a file over 5 GB, and a realistic mixed deposit.
Use RFC 010's large-deposit fixture if it is still available, recording its manifest.
Repeat each comparable run at least three times and include source-preparation time:
a preloaded or warm-cache result is not an end-to-end comparison with a cold baseline.

| Measurement | Why |
|---|---|
| Source preparation, binary staging, commit, and total elapsed time separately | Distinguish moved work from removed work |
| Per-binary request duration and failures | Fetching still occupies an API request |
| Importer and Fedora CPU/memory | Determine whether load is reduced or merely shifted |
| S3 reads/requests, NAT bytes and ALB traffic | Verify the proposed data-path benefit |
| Peak disk usage, cleanup and reserved capacity | Derive safe admission requirements |
| Implementation and operational changes | Include mount/host or HTTPS-adapter complexity |

### Failure and correctness checks

- Compare target paths, metadata, digests and OCFL version boundaries with the baseline.
- Supply a wrong digest and ensure the import cannot be reported as successful.
- Test a missing source, denied access, expired HTTPS access and interrupted source reads.
- Test a source that accepts a connection but then stalls. Cancel the importer request and
  measure whether and when Fedora stops fetching, releases resources and permits recovery.
  Do not assume client cancellation stops Fedora's source read.
- Inspect successful and failed runs for signed-URL query strings in Fedora logs, importer logs
  and job results; record any redaction changes required before production.
- Exercise source mutation protection, mount loss and workspace cleanup where applicable.
- Kill the importer during a source fetch and during commit; record the final Fedora outcome
  and whether the existing platform reports it correctly. Record reconciliation gaps explicitly.
- Measure capacity and cleanup under controlled limits; derive the required admission margin.
  If disk exhaustion is exercised, isolate it from shared environments.
- Confirm no failure produces a falsely successful or silently partial import.

Coordinated reservations and rejection/deferral before writes begin are production acceptance
requirements, to be implemented and tested before adoption rather than assumed to exist for
this spike.

### Exit criteria

Produce a comparison with measurements, failure outcomes, and a recommendation:
uniform fetching, a mixed policy, or retaining streaming. Set acceptable performance and
resource budgets before the full comparison; do not choose a threshold retrospectively.

Recommend adoption only if correctness is preserved and a measured reduction in relay traffic,
resource use or transfer failures justifies the added complexity. A few successful runs do not
prove improved long-term reliability. No commit-time improvement is assumed.
If a route cannot pass its compatibility checks, record it as blocked rather than treating
another route's success as evidence for it.

## 8. Relationship to RFC 010 and proposed decision

Bring T12 forward as a delivery and capacity spike, broadened to include local sources and
mixed deposits. Do not defer obvious network and deployment safety fixes while it runs.

Retain private Fedora connectivity, S3 gateway routing, deployment safeguards, commit
reconciliation and recovery runbooks from RFC 010. Do not increase import concurrency before
capacity admission and reconciliation are adequate.

**Decision requested:** approve this investigation, not an EC2 migration or a new production
delivery policy. Choose those from evidence. File-delivery improvements can simplify the importer
without changing preservation semantics, but cannot by themselves solve Fedora's synchronous commit.
