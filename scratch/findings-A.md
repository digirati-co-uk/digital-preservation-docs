# Findings: Import Jobs, Import Job results, Exports, Workflows

Discrepancies between `documentation/02-Preservation-API.md` (~1139-1407),
`documentation/06-Quickstart-preservation-workflow.md` and the code, found while writing
`preservation-api/import-jobs`, `import-job-results`, `exports` and all of `workflows/`.
Verified against `C:\git\uol-dlip\digital-preservation\src\DigitalPreservation` on branch
`feature/multiple-deposit-buckets`.

## Documentation errors (site now says what the code does)

- **The ImportJob operation lists are camelCase, not PascalCase.** Every JSON example in 02 and 06
  spells them `ContainersToAdd`, `BinariesToAdd`, `ContainersToDelete`, `BinariesToDelete`,
  `BinariesToPatch`, `ContainersToRename`, `BinariesToRename`. `Common.Model/Import/ImportJob.cs`
  gives the first five explicit `[JsonPropertyName]` values in camelCase; the two rename lists have
  no attribute at all and fall back to ASP.NET Core's default camelCase (Preservation.API sets no
  `JsonSerializerOptions`, so `JsonSerializerDefaults.Web` applies). `src/mets-id-migration` reads
  `binariesToPatch`, `binariesToRename` etc. in camelCase and works, which confirms it.

- **`ImportJob.sourceVersion` is an object, not a string.** 02's property table says "The value is
  a string of the form 'v1', 'v2', 'v3'". It is an `ObjectVersion`:
  `{ "mementoTimestamp": ..., "mementoDateTime": ..., "ocflVersion": "v2" }`. On `ImportJobResult`
  `sourceVersion` *is* a plain string, so the two resources genuinely differ and the old doc
  described the result's shape for both.

- **`ImportJobResult.originalImportJobId` does not exist.** Both 02 and 06 show that key in their
  JSON examples; the property is `originalImportJob` (the table in 02 gets it right, the example
  does not).

- **`"ArchivalGroup"` in the ImportJobResult examples should be `archivalGroup`.** Capitalised in
  both 02 and 06.

- **`errors` is null, not `[]`, when there are none.** `Error[]? Errors` with no initialiser and no
  `JsonIgnore`, so a fresh result serialises `"errors": null`. Both old examples show `[]`.

- **The ImportJobResult examples omit `sourceVersion`, `binariesRenamed` and `containersRenamed`.**
  All three are serialised. (02's property table lists them; its example doesn't.)

- **06's "no export" section POSTs to the wrong endpoint.** The prose says "you POST the partial
  Deposit to the /deposits endpoint rather than /deposits/export", and the code block immediately
  below says `POST /deposits/export`. Corrected on `workflows/update-without-export`.

- **02's execute example POSTs to `/deposits/e56fb7yg/importJobs`** (capital J) while the diff
  reference `id` it pairs with is lower-case. That combination does not work - see the
  case-sensitivity finding below.

## Not in the old documentation at all

- **A Deposit is good for one Import Job.** `ImportJobsController.ValidateDeposit(deposit, 0)` runs
  on *both* `GET .../importjobs/diff` and `POST .../importjobs`, and returns `409 Conflict` ("There
  are existing import jobs for this deposit") if the deposit has any ImportJobResult whose status is
  not `completedWithErrors`. So a deposit that has been preserved cannot even be diffed again. The
  old docs never mention it, and it is the single most surprising thing about the workflow.
  Documented on `import-jobs` and repeated on `workflows/overview`.

- **`suppressActivityStreamEvent`** (issue #188 step 3) post-dates the old documentation. Fenced by
  the `FeatureFlags:EnableMetsIdNormalisation` flag *and* by a content check (exactly one
  `binariesToPatch`, of a METS file, nothing else) - the latter re-checked after a diff reference
  has been expanded. Documented on `import-jobs`.

- **How the BagIt `data/` prefix appears in a diff.** `WorkspaceManager.GetCombinedDirectory`
  returns the *apparent* root (the `data` directory) for a BagIt layout, and `GetDiffImportJob`
  passes `FolderNames.GetFilesLocation(files, isBagIt)` as the origin root. So `id` paths carry no
  `data/`, `origin` URIs do, `source` is the deposit root, and the BagIt tag files (above `data/`)
  are never preserved. Documented on `import-jobs` and `workflows/bagit-deposit`.

- **Renames change the `name`, never the slug.** `PopulateDiffTasks` fills the rename lists from
  `existing.Name != sourceBinary.Name`. 02 documents the lists in a code comment only ("This cannot
  change the slug (path) but can change the name") and not in its property table.

- **The failure modes of diff generation.** 422 for a file in the deposit but not the METS, a METS
  entry with no digest, files with no checksum from any source, a non-empty folder missing from
  METS; 409 for a digest that disagrees between METS and deposit; 400 for size/content-type
  disagreement, colliding URI-safe names, and a binary with no file in the deposit. Tabulated on
  `import-jobs`.

- **`GET /depositarchivejobs/{id}` takes the DEPOSIT id**, not a job id, and returns the most
  recent archive job for that deposit. Documented on `exports`.

- **The Preservation API does not need you to poll.** `StorageImportJobsService` (a
  `BackgroundService`) reads the Storage API's import-job activity stream every 60s and calls
  `GetImportJobResult`, which is what updates the stored result *and* moves the Deposit to
  `preserved`/`error`. On failure it backs off for 30 minutes. Documented on
  `import-job-results` and `workflows/reading-the-activity-stream`.

## Looks like a code bug

- **`ImportJobResult.importJob` comes back pointing at the Storage API.**
  `ExecuteImportJobHandler` sends a copy of the job through `MutatePreservationImportJob`, which
  rewrites its `Id` to the storage host. `QueueImportJob` then sets
  `ImportJobResult.ImportJob = importJob.Id` - the storage-host URI - and the return trip only
  rewrites `Id`, `CreatedBy` and `LastModifiedBy` (`MutateStorageBaseUris`), not `ImportJob`. So an
  API client is handed a URI on a host it cannot reach and should not know about. 02's example
  shows a Preservation API URI, which is what it ought to be. The site documents the property as
  "the `id` of the job that was submitted" without claiming which host.

- **Refusing an old-version export of a METS-less object is a 500.** `CreateDepositBase.EnsureMets`
  returns `Result.Fail(ErrorCodes.UnknownError, "If exporting an Archival Group that doesn't have
  a METS, you can only export the HEAD version.")`, and `ResultX.ToProblemDetails` maps
  `UnknownError` to 500. This is a caller error and should be 400. The site describes the rule
  without giving a status code.

- **`ArchiveJobResult` is returned with `id` and `status` always null.**
  `ResourceMutator.MutateDepositArchiveJob` sets `DepositId`, `Errors`, `DateBegun` and
  `DateFinished` and nothing else, so the resource has no `id` of its own (unlike every other
  resource in the API) and its declared `status` ("Success or failure") is never populated. The
  site says so explicitly and tells callers to read `dateFinished` + `errors` instead.

- **The diff-reference match is case-sensitive and path-shaped.**
  `ImportJobsController.IsPostedDiffReference` does
  `importJob.Id.ToString().EndsWith(Request.Path + "/diff")`. `GetDiffUri` lower-cases the whole
  diff URI it puts in `originalId`, so a client that POSTs to `/deposits/{id}/ImportJobs` (ASP.NET
  routes case-insensitively, so this succeeds) with the lower-case `originalId` is silently not
  recognised as a diff reference; the body then fails `JobDoesNotBelongToDeposit` with "Import job
  must declare which Deposit it is for", which is a confusing way to report a casing problem. A
  case-insensitive comparison, or matching on the route rather than the raw path, would fix it.
  The site tells callers to use the lower-case path.

## Fragile rather than wrong

- **`ContainersToRename` and `BinariesToRename` are the only ImportJob properties with no explicit
  `[JsonPropertyName]`.** They currently serialise correctly by convention over the wire. But the
  same model is also serialised directly with `JsonSerializer.Serialize` (in
  `ExecuteImportJobHandler.Duplicate` and when storing `ImportJobJson` on the entity), where
  `JsonSerializerDefaults.Web` does **not** apply and those two names come out PascalCase while
  every other property keeps its attribute name. Round-tripping through `Duplicate` happens to be
  symmetrical, so nothing breaks today; it is still worth pinning the names. Flagged in an Aside on
  `import-jobs`.

## Could not verify

- None of the samples on these pages have been run: the dev API is behind a private load balancer
  and the VPN was not connected. In particular the minimal METS produced by
  `preservation-docs-client/workflows/own_mets.py` is written from `MetsParser` (a `TYPE="physical"`
  structMap, `mets:file/@ADMID` -> `mets:techMD` -> `premis:fixity`/`premis:size`, directories
  inferred from `FLocat` hrefs, `LABEL` on the file div supplying the name) and modelled on
  `playwright/PreservationApi/samples/10315s/10315.METS.xml`, but has not been through the parser.
  Run `python -m workflows.w02_preserve_first_time` against dev before trusting it.
- The site build was not run (the brief forbade it). Every internal link on these eleven pages was
  checked by script against the `.mdx` files present, and all resolve - including the forward links
  to `activity-stream`, `versions-and-storage-map` and `tool-outputs-and-pipelines`, which landed
  from other agents during this session. Anchors within those pages were not checked.
