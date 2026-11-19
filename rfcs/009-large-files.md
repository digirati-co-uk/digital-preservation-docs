# RFC 009: Preserving files larger than 5 GB

**Status: draft for discussion.** This paper proposes how the platform should accept, preserve and
export individual files larger than 5 GB, which it cannot handle today. It covers the platform
changes and an operator route that works without any UI work. A UI for large uploads is left for
later.

## The situation

A depositor has a deposit with three 10 GB files in it, and some much smaller ones. The small files
are no problem. The three large ones cannot be preserved today.

The 5 GB line comes from S3, not from us:

- A single `PutObject` is limited to 5 GB, so anything larger has to be uploaded as a **multipart
  upload**, in parts.
- A single `CopyObject` is also limited to 5 GB. Copying anything larger needs a multipart copy.
- For a multipart upload, S3 cannot store a SHA-256 of the whole file. Full-object checksums on
  multipart uploads are only available for the CRC algorithms. For SHA-256, S3 only stores a
  *composite* checksum: a checksum of the part checksums, which is not the SHA-256 of the file
  ([S3: checking object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html),
  the table under "Multipart uploads").

That third point is the one that matters. The platform treats an S3 object's SHA-256 checksum
attribute as the SHA-256 of the file, everywhere:

- when it reads the deposit's files, the S3 checksum becomes the file's digest;
- the UI upload asks S3 for a SHA-256 and compares it with the one the browser computed;
- export copies each file and checks the SHA-256 S3 returns against the one in the OCFL inventory.

Above 5 GB, that assumption cannot hold, whatever tool uploads the file.

## How the platform establishes a file's digest today

Before preserving, the diff gathers every SHA-256 it can find for each file and requires exactly
one: none, or two that disagree, and the file is refused. The sources are:

| Source | Where it comes from |
|---|---|
| The deposit file's S3 checksum | Set by S3 when the upload asked for SHA-256 (the UI always does) |
| A BagIt `manifest-sha256.txt` | Supplied by the depositor; ignored for a file modified after the manifest was written |
| The file's METS fixity | From a supplied METS (Archivematica, Goobi, EPrints), or written by the platform: the pipeline records Siegfried's SHA-256 here |

At import, the Storage API streams the file from S3 into Fedora with the agreed digest, and Fedora
computes its own. A mismatch fails the import. **That is a genuine end-to-end check**: the bytes
preserved are the bytes the agreed digest describes.

## What breaks above 5 GB

| Step | Today | Above 5 GB |
|---|---|---|
| Upload through the UI | Limit 2 GB; the browser reads the whole file into memory to hash it | Not possible |
| Upload directly to S3 | Works | Works, but the object has only a composite SHA-256, or none |
| Reading the deposit | S3 SHA-256 taken as the file's digest | A composite value is not a file digest. How the current code handles one is untested: it may fail to parse, or be read as a wrong digest that conflicts with every real one |
| Virus scan | See [#371](https://github.com/digirati-co-uk/digital-preservation/issues/371): files over 25 MB are currently skipped and recorded as clean | ClamAV cannot scan any file over 2 GB, at any setting. See section 4 |
| Import | Streams from S3 into Fedora, which verifies the digest | Should work, but no single file over 5 GB is known to have been imported |
| Export | One `CopyObject` per file, verified against the SHA-256 S3 returns | `CopyObject` fails over 5 GB, and a multipart copy returns no whole-file SHA-256 to verify against |

## Proposal

### 1. Separate *declared* digests from *observed* ones

The diff's rule — exactly one agreed SHA-256 per file — stays. What changes is where a digest may
come from, and naming the two kinds:

- A **declared** digest comes from the depositor: a checksum computed where the file lives before
  upload, a BagIt manifest, or a supplied METS.
- An **observed** digest is computed by the platform from its own copy: S3's whole-object SHA-256
  for a single-part upload, the pipeline's Siegfried hash, and Fedora's own at import.

Two concrete changes follow:

- **A composite checksum is no digest at all**, not a wrong one. The deposit reader checks the
  object's checksum type and ignores a composite SHA-256, instead of trying to read it as a file
  digest.
- **A declared digest can travel with the object**, as S3 user metadata written when the upload
  starts, for example `x-amz-meta-sha256`. The deposit reader treats it as the file's deposit
  digest when the object has no whole-object SHA-256. S3 does not verify user metadata, and does
  not need to: it is a declaration, which the pipeline's observed hash then corroborates, and which
  Fedora checks once more against the bytes at import.

Every SHA-256 the platform holds about a file still has to agree. A declared digest that the
pipeline contradicts stops the deposit at the diff, exactly as a mismatch does today.

**Decision A.** User metadata or an object tag for the declared digest? Metadata can only be set
when the object is written. A tag can be added afterwards without rewriting the object, which is
how AWS's own large-file example stores a full-object SHA-256. Metadata is proposed, because a
declaration should be made by whoever uploads the file, at the time they upload it.

### 2. An operator route, before any UI work

With change 1 in place, a deposit like the example can be preserved like this:

1. Create the deposit as usual, and upload the small files however you like.
2. Upload each large file directly to the deposit's `objects/` folder with the AWS CLI. Either:
   - declare its SHA-256 in metadata (`--metadata sha256=<hex>`); or
   - upload with no checksum options at all, and include a BagIt `manifest-sha256.txt` covering
     the large files. This needs no new code.
3. Run the pipeline. It adds the files to the METS with Siegfried's SHA-256, which must agree with
   the declared digest.
4. Create the diff and preserve.

The BagIt variant may already work today. An upload with no checksum options gets S3's default
CRC64 checksum, so it has no SHA-256 for the deposit reader to misread. Trying that first is part
of the validation below.

**Decision B.** Should the platform require a *declared* digest for files above some size, rather
than accept the pipeline's observed hash alone? Without one, preservation proves fixity from the
moment the file reached S3, but not that the upload itself was faithful. Today the pipeline-only
route is already possible for files of any size uploaded directly to S3, and the nightly e2e suite
exercises it.

### 3. Multipart export

Export must use a multipart copy (`UploadPartCopy`, or the SDK's transfer utility) for objects over
5 GB. A multipart copy returns no whole-file SHA-256, so verification has to change. The proposal:

- copy with a multipart copy;
- then verify by streaming the copy and hashing it, comparing against the OCFL inventory's digest;
- write the result to the copy as its declared digest (change 1), so the exported deposit's files
  carry a usable digest when it comes back for a new version.

Re-reading 10 GB costs time. It is only needed above 5 GB, where it is the only check available.

### 4. Virus scanning: say what wasn't scanned

ClamAV cannot scan a single file over 2 GB. Its own configuration documentation says so: "Technical
design limitations prevent ClamAV from scanning files greater than 2 GB". No setting changes that,
so every file this RFC is about will go unscanned by the pipeline.

The fix for #371 ([#372](https://github.com/digirati-co-uk/digital-preservation/pull/372),
[#373](https://github.com/digirati-co-uk/digital-preservation/pull/373)) makes that visible. With
`AlertExceedsMax` on, ClamAV reports such a file as `Heuristics.Limits.Exceeded.MaxFileSize`, and
the platform records a third PREMIS outcome, `Not scanned`, instead of `Pass`. Tested locally with
ClamAV 1.5.4, the version in the pipeline image: files of 2.5 GB, 4.1 GB and 5 GB were each refused
at once, without being read.

"Too big to scan" starts well below 5 GB in practice. ClamAV also stops any scan that runs past
`MaxScanTime`, which is 2 minutes by default, and reports that as not scanned too. Locally, on one
CPU, ClamAV scanned at about 15–25 MB/s:

- a 1.9 GB file took 80–119 seconds, so only just finished;
- four 600 MB files, scanned in parallel as the pipeline does, all ran out of time together.

Raising `MaxScanTime` is a #371 matter. The point for this RFC is that *not scanned* is a normal
outcome for large files, whatever its cause, and the platform should treat it as one.

For a file ClamAV can't scan, the options are:

- **Record it, and make it visible.** This is the proposal: the outcome is `Not scanned` with the
  reason, and preservation can go ahead.
- **Unpack container formats.** A zip, tar or disk image over 2 GB could be unpacked and its members
  scanned one by one. ClamAV already does this for archives within its limits. Above them, it would
  need our own unpacking step. This is worth doing only once such deposits arrive.
- **Use a scanner without the 2 GB limit**, for example AWS's malware scanning for S3. Its size
  limits, its cost, and how its result would be recorded as PREMIS provenance would all need
  checking first.
- **Not viable: scanning the file in chunks.** ClamAV identifies a file's type and parses its
  format, and a chunk has neither. A signature that crosses a chunk boundary would be missed. A clean
  result from chunks would claim less than `Pass` means.

A later scan event supersedes an earlier one. So a file recorded `Not scanned` today can be scanned
again if a better option arrives, and the new outcome becomes its current status.

**Decision C.** Should preserving a file with a `Not scanned` outcome need an explicit
acknowledgement? For example, a flag on the preserve request, or a confirmation in the UI. The
proposal is yes. The outcome should be shown on the deposit and in the import job, and the preserve
request should say that it accepts it. A result that is recorded but never looked at is how #371
went unnoticed.

### 5. Validate on dev before promising anything

Before this is offered to depositors, one 10 GB file goes through every step on dev:

1. The BagIt variant of the operator route, with today's code.
2. The same with change 1 in place, using declared metadata.
3. Pipeline: the time for three such files. The pipeline reads deposit files through an S3 mount,
   so it needs no local copy, but Siegfried hashes every byte through it. The virus scan should
   record each file as *not scanned* (depends on #371).
4. Import: the Fedora PUT and transaction commit at this size, and the OCFL write to S3.
5. Export of the preserved file, then a new version built from that export.

## Not in this RFC

- **Uploading large files through the UI.** That needs the browser to hash the file in chunks
  rather than all at once, and to upload parts directly to S3 through presigned URLs rather than
  through the UI server. It builds on change 1, and deserves its own paper when it is needed.
- **The virus-scan limits for files under 2 GB**, which are part of
  [#371](https://github.com/digirati-co-uk/digital-preservation/issues/371). That includes `MaxScanTime`.
