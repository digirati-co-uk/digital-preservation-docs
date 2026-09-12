# Findings: Storage API and Internals pages (brief 7)

Discrepancies between `documentation/03-Storage-API.md`, `documentation/01-Introduction.md`, the code
repo's `CLAUDE.md`, and the code as it stands on `feature/multiple-deposit-buckets`. Same style as
`findings.md`: what was found, where, what the code actually does, docs error or code bug.

## Open

- **The Storage API activity stream never emits `Create`, and the object type is `ImportJob`.**
  (storage-api/activity-and-content) `ImportJobResultStore.MakeActivity`
  (`Storage.API/Features/Import/Data/ImportJobResultStore.cs`) hard-codes
  `Type = ActivityTypes.Update` with the comment "For import jobs this is always an Update", and sets
  the activity object's `type` to `nameof(ImportJob)` even though its `id` is the **import job
  result** URI (`importJob.ImportJobResultUri`). `documentation/03-Storage-API.md` shows both `Create`
  and `Update` entries and `"type": "ImportJobResult"`. Documentation error for the `Create`/`Update`
  part; the `type: "ImportJob"` on a result URI looks like a **code bug** - it disagrees with the
  Preservation API stream, whose objects are typed to match their ids. The site documents what the
  code emits and flags the mismatch.

- **`seeAlso` in the Storage API activity stream is an array, not an object.**
  (storage-api/activity-and-content) `ActivityObject.SeeAlso` is a List of ActivityObject and
  `MakeActivity` populates it with a single-element collection. The old doc shows
  `"seeAlso": { "id": ..., "type": "ArchivalGroup" }`. Documentation error.

- **The old doc's activity-collection `first` link is missing the `pages` segment.**
  (storage-api/activity-and-content) `documentation/03-Storage-API.md` shows
  `"first": { "id": "https://storage-api/activity/importjobs/1" }` while `last` correctly has
  `/pages/40`. `GetImportJobsOrderedCollectionHandler` builds both with
  `converters.ActivityUri("importjobs/pages/N")`. Documentation error (a typo that would 404).
  The code also emits `startTime`, `partOf` and `next`, none of which the old doc shows.

- **Import jobs can express renames, and the Storage API silently ignores them.**
  (storage-api/import) `ImportJob.ContainersToRename` / `BinariesToRename` exist on the model, the
  Preservation API's `GetDiffImportJob` *populates* them when a `name` has changed (lines 318 and
  326), `ImportJobsController` tests them when deciding whether a job is empty, and
  `ResourceMutator` rewrites their URIs. But `ExecuteImportJobHandler` in the Storage API has no loop
  for either list - the only mention of `BinariesToRename` is in `PreProcessValidateImportJob`'s
  union of binaries whose ids are checked for a fragment character. So a diff whose only change is a
  display name executes, reports `completed`, and changes nothing; `ImportJobResult.containersRenamed`
  / `binariesRenamed` are always empty. The model carries the comment "TODO: (not for demo) - change
  name (dc:title) of containers and binaries", so this is known, but nothing in the API tells a
  caller. **Code bug / unimplemented feature.** The site documents the lists as accepted but not yet
  performed.

- **A Binary's `content` URI is on the Storage API host and carries no version.**
  (storage-api/activity-and-content; also affects preservation-api/repository)
  `Converters.ConvertToContentUri` rewrites the Fedora URI to `Converter:StorageRoot` + `content/...`
  with no query string. `Preservation.API/Mutation/ResourceMutator` rewrites only `id`, `createdBy`,
  `lastModifiedBy` and `partOf` - **not** `content` - so a Binary fetched from the Preservation API
  hands you a Storage API URL that most callers cannot reach. `repository.mdx` currently shows
  `"content": "https://preservation-api.example/content/...?version=v2"`, which is wrong on both
  counts. And `Storage.API/Features/Binaries/ContentController` takes no `version` parameter: it
  resolves the path through Fedora and streams `binary.Origin`, i.e. always the current version's
  bytes. Related to the existing `findings.md` entry "Binary `content` URI is not served by the
  Preservation API"; the same decision covers all of it.

- **The old doc's ImportJob example uses PascalCase property names.**
  (storage-api/import) `documentation/03-Storage-API.md` shows `"ContainersToAdd"`,
  `"BinariesToAdd"`, `"ContainersToDelete"` and so on. The serialised form is camelCase
  (`JsonPropertyName("containersToAdd")` etc.). The PascalCase body happens to work on input only
  because ASP.NET Core's System.Text.Json defaults to case-insensitive binding. Documentation error;
  the site uses the names the API actually emits.

- **The old doc's ImportJob example omits `isUpdate` and types `sourceVersion` as a string.**
  (storage-api/import) `ImportJob.IsUpdate` "must be explicitly set to true to allow an update of an
  existing ArchivalGroup"; without it `ExecuteImportJobHandler` fails the job with
  `Conflict` ("Archival Group is not null for new Import"). `ImportJob.SourceVersion` is an
  `ObjectVersion` object (`mementoTimestamp` / `mementoDateTime` / `ocflVersion`), not a string - it
  is `ImportJobResult.SourceVersion` and `Export.SourceVersion` that are plain strings. Documentation
  error.

- **`POST /import` requires `lastModifiedBy`, then reads `createdBy`.**
  (storage-api/import) `QueueImportJobHandler` rejects a job with no `LastModifiedBy` as
  `Unauthorized` (401) and derives the result's `createdBy`/`lastModifiedBy` agent from it.
  `ExecuteImportJobHandler` then takes the caller identity it writes into Fedora from
  `importJob.CreatedBy!` - a null-forgiving dereference on a property nothing has validated. A job
  with `lastModifiedBy` but no `createdBy` passes the queue check and throws a
  `NullReferenceException` in the executor, which is caught only as a generic failure. **Code bug**
  (an unchecked required input); the site says to send both.

- **A METS-only export that throws produces a 500, not an Export with `errors`.**
  (storage-api/export) `ExecuteExportHandler`'s catch block builds
  `new Uri(export.Id + "#error")`. For `POST /exportMetsOnly` the handler is invoked directly with
  a null identifier and the caller's own body, so `export.Id` is null (only `QueueExportHandler`
  mints one). Concatenating null gives the relative string `"#error"`, and `new Uri("#error")` throws
  `UriFormatException` *from inside the catch*, escaping the handler. Every other export failure mode
  is reported in the `errors` array as designed. **Code bug**; the site describes the intended
  behaviour and notes that a hard failure surfaces as a 500.

- **`GET /FedoraSearch` with no `pageSize` returns every match.**
  (storage-api/activity-and-content) `FedoraSearchController` passes `page` and `pageSize` through as
  nullable ints; its guard (`page < 0 || pageSize <= 0 || pageSize > 500`) is false for nulls, and
  `FedoraDB.GetSimpleSearch` interpolates them straight into `LIMIT @pageSize OFFSET @offset`.
  Postgres treats `LIMIT NULL` as no limit and `OFFSET NULL` as 0, so omitting `pageSize` runs an
  unbounded query - despite `SearchCollectiveFedora` declaring defaults of `PageSize = 50`,
  `Page = 0` (which are overwritten with the nulls before they are ever used). The response also
  echoes back `page` and `pageSize` as `null` in that case. **Code bug**, small but a real
  denial-of-service shape on a large repository. The site documents both parameters as effectively
  required.

- **Storage API search page numbers are zero-based; activity stream page numbers are one-based.**
  (storage-api/activity-and-content) `GetSimpleSearch` computes `offset = pageSize * page`, so
  `page=0` is the first page of search results. `GetImportJobsOrderedCollectionPageHandler` computes
  `startIndex = (page - 1) * pageSize`, so `/activity/importjobs/pages/1` is the first page. Two
  conventions in one API. Not documented anywhere before; the site states each explicitly.

- **Fedora search matches paths only, and only Binaries.**
  (storage-api/activity-and-content) The SQL is
  `WHERE S.fedora_id ILIKE '%text%' AND mime_type is not null`, joined from `containment` to
  `simple_search` in Fedora's own database - not Fedora's REST search, and not the `name` (dc:title)
  of anything. The `mime_type is not null` clause restricts results to Binaries. Undocumented before;
  worth knowing before anyone treats it as a discovery service.

- **`GET /import/test-path/...` returns a meaningless body.**
  (storage-api/import) `ImportController.TestArchivalGroupPath` runs the validation, then returns
  `Ok(new ArchivalGroup())` - a comment calls it `dummyAgAsContainer`. So a caller gets an empty
  ArchivalGroup whether the path is free and usable or holds an existing Archival Group with 3,000
  files. Only the status code carries information. Harmless but confusing; the site says to read the
  status, not the body. It would be more useful to return the real Archival Group when there is one
  (the handler already fetched it).

- **Export cannot be run out of process.** (storage-api/export, internals/deployment)
  `Storage.API/Program.cs` throws `NotSupportedException("Separate export service not yet
  implemented!")` when `FeatureFlags:UseLocalHostedServiceForExport` is false - that is, the Storage
  API refuses to start. The flag exists but has exactly one valid value. Not a bug, but it means the
  import/export symmetry implied by the `ImportExport` config section (which has an
  `ExportJobTopicArn` and `ExportJobSqsQueueName`) does not exist yet.

- **The `ImportExport` config section is split across two services and neither example is complete.**
  (internals/deployment) `ImportOptions` declares all four of `ImportJobTopicArn`,
  `ImportJobSqsQueueName`, `ExportJobTopicArn`, `ExportJobSqsQueueName` as `required`, but options
  binding does not enforce `required`. `Storage.API/appsettings.Example.json` supplies only the two
  topic ARNs and `Storage.API.Importer/appsettings.Example.json` only the two queue names. That
  happens to match what each process uses (the API publishes to SNS, the importer consumes from SQS),
  so nothing breaks; the `required` modifiers just overstate the case. Informational.

- **`Storage.API/appsettings.Example.json` ships `FeatureFlags:DisableAuth` as `"true"`.**
  (internals/deployment) Already recorded in `findings.md` from the authentication page, and called
  out again on the deployment page as a caution, because that page is the one that tells people to
  start from the example files. Still true. Code/config bug: the example should default to secure.

- **Six ECR images are built and deployed, not five.** (internals/deployment) The code repo's
  `CLAUDE.md` lists `dlip-pres-storage-api`, `-storage-api-importer`, `-preservation-api`,
  `-preservation-ui`, `-pipeline-api`. `.github/workflows/build.yml` also builds
  `deposit-archiver` from `Dockerfile.DepositArchiver`, and `deploy.yml` retags
  `dlip-pres-deposit-archiver`. Documentation error in the code repo's CLAUDE.md.

- **The deposit archiver is retagged but never restarted.** (internals/deployment)
  Every other job in `.github/workflows/deploy.yml` pairs `ecr-retag` with `ecs-bounce`;
  `deploy-deposit-archiver-builder` has only the retag step. The archiver is a Lambda
  (`LambdaEntryPoint.cs`, `serverless.template`), and retagging an image does not update a Lambda's
  function code, so it is not obvious that anything is deployed by this. Looks like an
  **incomplete deployment job**; worth confirming with whoever owns the archiver. The site describes
  the pipeline as it is written and does not claim the archiver is deployed by it.

- **`docker-compose.yml` will not run the stack.** (internals/deployment) The code repo's
  `CLAUDE.md` offers `docker compose build && docker compose up` as "build and run all services".
  The file defines `storage`, `preservation`, `ui` and a single `db` (the preservation database on
  5433). There is no storage database, no Pipeline API, no importer, and the `storage` service has no
  `env_file`, so it starts with no Fedora, no AWS and no database configuration.
  `docker-compose.local.yml` - the one that is actually used - brings up the three Postgres
  databases, the iiif-builder and a local ClamAV, and the .NET services are run from the IDE.
  Documentation error in the code repo's CLAUDE.md; the site documents `docker-compose.local.yml`
  plus `dotnet run` as the local story.

- **The iiif-builder's database table is created by hand.** (internals/iiif-builder)
  `src/iiif-builder/app/db.py` ends with the `CREATE TABLE archival_group_activity` statement in a
  comment. There is no migration step and no create-if-not-exists at startup, so a new deployment
  needs someone to run that SQL before the service can record anything. Worth turning into a startup
  migration; documented on the site as a deployment step.

- **`ACTIVITY_CUTOFF_DATE` accepts the literal string `now`.** (internals/iiif-builder)
  `ArchivalGroupActivity.get_latest_end_time` special-cases `"now"` (case-insensitive) to mean "start
  from this moment", falls back to the current time if the value will not parse, and - when the
  variable is unset and the table is empty - starts from a hard-coded `2025-04-08`. None of this was
  documented; it is the most useful knob on the service and the site now describes it.

- **`get_internal_iiif_uris` and `should_process` use `lstrip` where they mean `removeprefix`.**
  (internals/iiif-builder) `app/identity_service.py` does
  `public_manifest_uri.lstrip(settings.REWRITTEN_PUBLIC_IIIF_PRESENTATION_PREFIX)` and
  `app/iiif_builder.py` does `path.lstrip('/').lstrip('repository/')`. `str.lstrip` strips any
  leading characters **from the set**, not the prefix string, so an Archival Group path beginning
  with any of r, e, p, o, s, i, t, y or / loses those characters too - for example
  `repository/story/x` becomes `y/x`. `should_process` then compares the mangled path against the
  configured prefixes, so a legitimate Archival Group can be skipped. `get_internal_iiif_uris` has
  the same flaw but is dead code (the main loop inlines the `removeprefix` version). **Code bug.**

- **The code repo's `CLAUDE.md` is stale about where the METS classes live.**
  (internals/workspace-manager) It places `MetsParser`, `MetsManager` and `PremisManager` in
  `Storage.Repository.Common/Mets/`; they are in the `DigitalPreservation.Mets` project. Already
  noted in `findings-F.md`; repeated here because the internals pointer page depends on it.

## Could not verify

- Nothing on these pages was exercised against a running instance: the dev API is behind the
  university VPN and the brief forbids starting a service. Every statement is from the source. The
  response bodies shown on the Storage API pages are constructed from the C# models and their
  JSON property-name and property-order attributes, not captured from the wire.
- The ECS/ECR names on the deployment page come from `.github/workflows/deploy.yml` variable
  references; the actual values are GitHub environment variables and were not read.

## Added while writing (same session)

- **The Storage API has no `/agents` route.** (storage-api/overview) `Converters.GetAgentUri` mints
  agent URIs against the Storage API root and writes them into `createdBy` / `lastModifiedBy` on
  every resource, but `Storage.API/Features` has no agents controller - only the Preservation API has
  one (`Preservation.API/Features/Agents/AgentsController.cs`). Those URIs 404.
  `documentation/03-Storage-API.md` says of Agents "This section is the same as the Preservation
  API", which is not true. Documentation error, plus a set of dangling URIs the Preservation API's
  mutator happens to rewrite onto a host where they do resolve.

- **A Storage API Import Job Result has `lastModified` and `lastModifiedBy`.** (storage-api/import)
  `preservation-api/overview.mdx` says "`ImportJob` and `ImportJobResult` have `created` and
  `createdBy` but not the `lastModified` pair, because they are never modified once submitted".
  `QueueImportJobHandler.CreateWaitingResult` sets all four, and `ExecuteImportJobHandler` updates
  `LastModified` as the job runs - the result is modified repeatedly, which is the whole point of
  polling it. The overview page's statement needs narrowing to `ImportJob`.

- **An Export is stored exactly as the caller sent it.** (storage-api/export)
  `ExportResultStore.CreateExportResult` serialises the caller's own `Export` object with only an
  `id` added; nothing sets `created`, `createdBy`, `lastModified` or `lastModifiedBy`. Every other
  resource in the platform has these filled in by the API. So there is no record of who asked for an
  export unless they chose to say. Looks like an oversight worth fixing, given that `exportedBy` is
  documented as an attribution the platform records.

- **`ImportJob` Containers carry an `origin` that is never read.**
  (storage-api/import) `documentation/03-Storage-API.md`'s example gives `containersToAdd` entries an
  `origin`. `ExecuteImportJobHandler` calls `CreateContainerWithinArchivalGroup(path, caller, name,
  ...)` and never looks at it. Harmless, but the example teaches callers to send something
  meaningless. Documentation error; the site's example omits it.

- **`FeatureFlags:UseLocalHostedServiceForPipeline` does nothing.** (internals/deployment)
  It is set in `Pipeline.API/appsettings.Example.json` (and the other Pipeline API settings files),
  but no code in the solution reads it - the only `UseLocalHostedService*` flags with readers are the
  Storage API's import and export ones. The Pipeline API always registers
  `PipelineJobExecutorService` as a hosted service. Same class of dead config as that service's
  `DisableAuth`, already recorded in `findings.md`. Misleading; either implement it or delete it.
