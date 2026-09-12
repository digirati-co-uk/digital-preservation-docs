# Findings: activity stream, versions/storage map, search, IIIF, vocabularies

Brief 5 (pages `preservation-api/activity-stream`, `versions-and-storage-map`, `search`, `iiif`,
`vocabularies`). Raw material: `documentation/02-Preservation-API.md` lines ~1408-1711.
Verified against the code at `src/DigitalPreservation` (branch
`feature/multiple-deposit-buckets`) and `src/iiif-builder`.

## Open

### Activity stream

- **The old doc's WARNING about `seeAlso` is correct and still true.** (activity-stream page)
  `GetArchivalGroupsOrderedCollectionPageHandler.MakeActivity` emits
  `object.seeAlso[0].id = ArchivalGroupEvent.ImportJobResult`, which
  `StorageImportJobsProcessor.ReadStream` set from `activity.Object.Id` of the **Storage API's**
  own import-job activity stream (`ImportJobResultStore.MakeActivity` uses
  `importJob.ImportJobResultUri`). `ResourceMutator.MutateStorageApiUri` is never applied to it,
  so the URI is on the Storage API host - which almost no consumer of the Preservation API can
  reach. The Preservation API has its own import job result under `/deposits/{id}/importjobs/...`
  and a mapping already exists in the DB
  (`PreservationContext.GetImportJobFromStorageImportJobResult`), so this is a code bug that could
  be fixed by mutating the URI at the point the event is written. Documented on the site as a
  caution: treat `seeAlso` as opaque and act on `object.id`.

- **`seeAlso` is a JSON array, not a single object.** (activity-stream page)
  `ActivityObject.SeeAlso` is `List<ActivityObject>?`; the old doc shows it as a bare object.
  Documentation error; the site shows the array.

- **The old doc's `first` link is wrong.** (activity-stream page) The example shows
  `"first": { "id": ".../activity/archivalgroups/1" }`. The code builds
  `GetActivityStreamUri("archivalgroups/pages/1")`, i.e. `.../activity/archivalgroups/pages/1`,
  the same shape as `last`. Documentation error.

- **The old doc's page example omits `partOf` and `next`.** (activity-stream page)
  `GetArchivalGroupsOrderedCollectionPageHandler` always sets `partOf` (pointing at the
  collection), sets `prev` when page > 1, and sets `next` when there are more items after this
  page. The old example shows only `prev`. Documentation error.

- **The page size is 100 and is not adjustable.** (activity-stream page)
  `OrderedCollectionPage.DefaultPageSize = 100`; nothing reads a page-size parameter. The old doc
  never said.

- **The first item in the published stream is a seed row pointing at `example.com`.**
  (activity-stream page) `PreservationContext.OnModelCreating` seeds an `ArchivalGroupEvent` with
  Id -1, EventDate 2024-01-01 and ArchivalGroup `https://example.com/archival-group`, needed to
  give the Storage-stream reader a starting watermark. It is not `Suppressed`, so
  `PublishedArchivalGroupEvents()` includes it and it surfaces as the first `Create` activity on
  page 1 of the public stream, with an `object.id` that is not in this repository. Harmless for a
  consumer reading backwards to a watermark, and iiif-builder's `should_process` prefix check
  rejects it anyway, but a consumer replaying from the start will meet it. Looks like a code bug
  (the seed row should be `Suppressed = true`); documented on the site as "tolerate objects you do
  not recognise".

- **POST `/activity/archivalgroups/collection` is a real endpoint for external callers, but it
  does not mean what its shape suggests.** (activity-stream page) It is authenticated like every
  other route, has no feature flag, and `playwright/PreservationApi/tests/push-activity-stream-update.spec.ts`
  exercises it as an ordinary API client (expects `204`). Nothing inside the platform calls it.
  What it does: validate that the body is an `Update` activity whose `object.type` is
  `ArchivalGroup` and whose `object.id` is on this Preservation API's host, ask the Storage API to
  confirm the path really is an Archival Group, then write an `ArchivalGroupEvent` with
  `FromVersion = "(push)"` - so the event appears in the stream as an `Update` with **no**
  `seeAlso`, and `endTime` set to the time of the POST, not to any version change. Its purpose is
  to make a downstream consumer re-process an object that has not changed in the repository
  (rebuilding a IIIF manifest after catalogue metadata changed, for example). Two things to be
  aware of, both documented: the `endTime`/`startTime` you send are ignored, and a push moves the
  stream reader's watermark (`GetLatestArchivalGroupEvent` is `OrderByDescending(EventDate)` and
  includes pushes), so there is no way to backdate one.

- **Suppressed events are invisible in the stream but still move the watermark.**
  (activity-stream page) `ArchivalGroupEvent.Suppressed` is set from the import job's
  `SuppressActivityStreamEvent` (used by the METS-ID migration). `PublishedArchivalGroupEvents()`
  filters them out of both the count and the page query; `GetLatestArchivalGroupEvent()`
  deliberately does not. Undocumented in the old docs; both XML doc comments explain why. The
  consequence for an external consumer is that `totalItems` is smaller than the number of import
  jobs that have run.

- **Deletions are not in the stream.** (activity-stream page) `ArchivalGroupEvent.Deleted` exists
  and both `MakeActivity` implementations carry a `// TODO: Deletions` comment; only `Create` and
  `Update` are ever emitted. Stated on the site as a limitation.

### Versions and the storage map

- **`hashes` is not the whole OCFL manifest.** (versions-and-storage-map page) The old doc says it
  is "equivalent to the manifest block in an OCFL Inventory". `OcflS3StorageMapper.GetStorageMap`
  builds `hashes` only from the entries of the *requested version's* `state` block, and only after
  dropping Fedora's own sidecar files (`IsFedoraMetadata`). So it is the manifest restricted to
  the files visible at that version. Documentation error, corrected on the site.

- **`files` and `hashes` exclude Fedora's internal metadata files.** (versions-and-storage-map
  page) Same method. Not mentioned in the old doc; it explains why the storage map lists fewer
  files than a raw listing of the OCFL object.

- **A Binary's `origin` is only populated when you are looking at the head version.**
  (versions-and-storage-map page) `FedoraClient.GetPopulatedArchivalGroup` calls
  `PopulateOrigins(storageMap, archivalGroup)` only when
  `archivalGroup.Version.Equals(archivalGroup.StorageMap.HeadVersion)`. To locate the bytes of a
  file in an older version you must use the storage map for that version. Not a bug, but not
  documented anywhere before.

- **`storageMap.archivalGroup` is a Fedora URI and is not rewritten.** (versions-and-storage-map
  page) `GetStorageMapHandler` returns the Storage API's `StorageMap` untouched, and
  `ResourceMutator` only rewrites `id`, `createdBy`, `lastModifiedBy` and `partOf` on
  `PreservedResource`s. The old doc says as much ("you are unlikely to have access to this"); the
  site keeps that, and notes it is the one URI in the response that is not a Preservation API URI.

- **The OCFL version label comes from the OCFL inventory, not from Fedora.**
  (versions-and-storage-map page) `FedoraClient.MergeVersions` pairs Fedora's Memento list with
  the inventory's version list *by index*, throwing if the counts or the timestamps differ.

### Search

- **The paging parameter is `pageNumber`, not `page`.** (search page) `SearchController.Search`
  binds `text`, `pageNumber`, `pageSize`, `type`, `otherPage`. The old doc's examples
  (`/search?text=...&page=2`) do nothing - the parameter is ignored and you get page 0 back.
  Documentation error, corrected on the site.

- **`text` and `searchType` are declared on the response but never populated.** (search page)
  `SearchCollection` has `text` and `SearchType` properties; `SearchRequestHandler.Handle` sets
  only `FedoraSearch`, `DepositSearch` and `Identifier`, so both are always `null` in the
  response. The old doc's example shows `"text": "pipeline"`. Looks like a code bug (the handler
  should echo them); the site documents them as always null and tells the caller to keep their own
  search term.

- **The search response has a third result set the old doc never mentions: `identifier`.**
  (search page) `SearchRequestHandler.GetIdentifier` asks the Leeds Identity Service for a record
  whose PID matches the search text, then (if that misses) whose CatIRN matches, and returns a
  single `Identifier` or null. This is a Leeds-specific extension - `Identifier`'s own XML comment
  says so. Documented as such.

- **`depositSearch` is `null`, not an empty page object, when nothing matches.** (search page)
  `GetDeposits` returns `null` early if the first page of results is empty. `fedoraSearch` is
  likewise null if the Storage API call fails. Clients must null-check both.

- **Deposit search also matches the deposit's own identifier.** (search page) The old doc says
  "the Deposit `id` last path element" - correct: the query matches `MintedId`, plus
  `ArchivalGroupName`, `SubmissionText` and `ArchivalGroupPathUnderRoot`, case-insensitively, as
  substrings.

- **`pageSize` is capped at 500, and `type`/`otherPage` are undocumented.** (search page)
  `pageNumber < 0`, `pageSize <= 0` and `pageSize > 500` all give `400`. `type` (`All`,
  `Deposits`, `Fedora`) does not restrict *what* is searched - both sources are always queried -
  it selects which result set `pageNumber` applies to, with `otherPage` paging the other one.
  That is what lets the UI page one list without disturbing the other.

### IIIF

- **The Archival Group Manifest's painting bodies point at `/repository/...` URIs, which return
  JSON, not bytes.** (iiif page) `GetArchivalGroupAsIIIFManifestHandler` passes an
  `originUriResolver` that maps each METS file to the Binary's **`id`** (its Preservation API
  repository URI), not to its `origin`, despite the name. Combined with the existing finding that
  the Preservation API does not serve `/content/...`, a IIIF client handed one of these manifests
  cannot fetch any image. The manifest is useful for its structure; it is not yet viewable.
  Needs a decision alongside the `content` URI finding in `findings.md`. Documented as a caution.

- **The Archival Group Manifest endpoint is not behind the IIIF feature flag; the deposit ones
  are.** (iiif page) `IiifController` (`GET /iiif/...`) is authenticated and always available.
  `GET /deposits/{id}/iiif-token/{token}`, its `POST` counterpart and all of `/media/...` carry
  `[RequireFeatureFlag("EnableIiifMediaEndpoints")]` and `[AllowAnonymous]`.
  `appsettings.Example.json` ships the flag as `"false"`.

- **`GET /deposits/{id}/iiif` is not itself behind the flag, so with the flag off it redirects
  into a 401.** (iiif page) The redirect action has no `RequireFeatureFlag` attribute; the target
  route does, and `RequireFeatureFlagAttribute` returns `401 Unauthorized` (not `404`) when the
  flag is off. A caller following the redirect gets a bare 401 with no explanation. Minor code
  smell; documented so the 401 is not mistaken for an auth problem.

- **The tokenised deposit routes are anonymous, and the token is the only protection.** (iiif
  page) `TokenService` mints a random 128-bit hex token held in the API's in-process
  `IMemoryCache` with an 8-hour *sliding* expiry, keyed both ways. Consequences worth documenting:
  the token is unguessable but bearer-like (anyone with the URL can read the deposit's files
  through `/media/...` and POST structure changes back); it dies when the API process restarts;
  and it will not work across more than one API instance behind a load balancer, because the cache
  is per-process. That last point looks like a real deployment constraint rather than a
  documentation matter - worth raising separately.

- **POSTing a Manifest back only ever writes logical structMaps.** (iiif page)
  `UpdateLogicalStructMapsFromManifestHandler` reads the manifest's `structures`, validates that
  every canvas referenced resolves to a canvas the manifest itself declares (else `400`), converts
  each root Range to a `LogicalRange` and calls `WorkspaceManager.SetLogicalStructMap`. Nothing
  else in the posted manifest is read: canvases are not created, deleted or renamed, no file is
  touched, and the manifest's own label and metadata are ignored. Returns `204`.

- **Round-tripping depends on hidden metadata pairs in the Ranges.** (iiif page)
  `ManifestBuilder.MakeRange` writes `Type`, `Name` and `id` into the Range's `metadata`, and
  `ManifestParser.RangeToLogicalRange` reads them back; a Range without them is treated as
  externally authored and given a fresh generated id, type `Collection` at the root and `Item`
  below it, and its label as the name. Access restrictions and record identifiers travel the same
  way (`access restriction`, `record identifier: <source>`), and `rights` carries the rights
  statement URI. An editor that drops or rewrites `metadata` will silently lose those values.

- **The media route only supports `source=deposit`.** (iiif page) Anything else is `400`. The
  `type` segment is one of `imagesvc`, `placeholder`, or anything else (`file`, `video`, `audio`
  are what the builder emits), which serves the deposit file directly with byte-range support.
  The image service is IIIF Image API 3 **level 0**: only `/full/{w,h}/0/default.jpg` and
  `/info.json`, and `info.json` is a hand-built dictionary that `404`s unless the file has
  `ExtentMetadata` with a pixel width and height - i.e. unless the pipeline has characterised it.

- **Only files under `objects/` with a known content type become canvases.** (iiif page)
  `ManifestBuilder.MakeCanvasesAndRanges` skips anything whose `LocalPath` does not start with
  `objects/`, anything with no `ContentType`, and any file that is the target of another file's
  METS link (a transcript, say) - those appear as supplementing annotations on the linked file's
  canvas instead. Files that are neither image, video nor audio get a grey placeholder canvas with
  a `rendering` link to the original.

### Vocabularies

- **`AccessConditions` and `RangeTypes` are per-instance configuration, and the controllers return
  an empty list when they are absent.** (vocabularies page) Both controllers bind
  `configuration.GetSection(...)` with a `?? []` fallback; there is no default list, no validation
  and no error. The values in `Preservation.API/appsettings.Example.json` (`dlip-open`,
  `dlip-2-restricted`, ... and `["Collection", "Item"]`) are one instance's choices, not the API's
  definition. Documented as such, with the example values clearly labelled as examples.

- **`AccessRestriction.All` is dead code that contradicts the configuration.** (vocabularies page)
  `DigitalPreservation.Common.Model/AccessRestriction.cs` has a static `All` list
  (`Open`/`Restricted`/`Staff`/`Closed`) that nothing reads - the controller binds from config
  instead, and the example config uses entirely different values. Harmless but misleading; a
  reader of the model class would conclude the vocabulary is fixed. Looks like leftover code.

## Resolved

(nothing yet)

## Added after drafting

- **Preserved-resource search only ever returns Binaries.** (search page) `FedoraDB.GetSimpleSearch`
  and `GetSearchCount` both end `AND mime_type is not null`, which excludes Containers and
  Archival Groups. The old doc calls the second result set "Preserved resources", implying both.
  Results are ordered `created DESC` (newest first), and the `ILIKE '%text%'` match is against the
  whole `fedora_id`, which begins `info:fedora/` - so a search for `fedora` matches everything.
  Documentation error in the old doc; the site says "preserved files".

- **`storageType` is `S3` or `FileSystem`, not `S3` or `file`.** (versions-and-storage-map page)
  The old doc's table says "either 'S3' or 'file'". `StorageTypes` defines `S3 = "S3"` and
  `FileSystem = "FileSystem"`, and the only implementation (`OcflS3StorageMapper`) always writes
  `S3`. Documentation error; the site says `S3` always, with `FileSystem` noted as defined but
  unused.
