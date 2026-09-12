# Handover: porting the documentation to the Starlight site

Written 2026-09-11 at the end of the first session. Read this, then `../CLAUDE.md` (conventions)
and `site-plan.md` (page slugs), before writing anything.

## Where we got to

Branch `docs-site` in this repo (created off `mets-profiles`, which is unmerged and holds the
02b–02e METS pages; when `mets-profiles` merges to main, rebase). Last commit: 8ae98b7.
The site builds clean (`cd site && npm run build`, 18 pages). Dev server: `cd site && npm run dev`
then http://localhost:4321/digital-preservation-docs/ .

Done and verified against code:

| Section | Pages | Samples |
|---|---|---|
| introduction | overview, concepts, components | – |
| mets | overview, mets-we-write, mets-we-write-descriptive, mets-we-read, identifiers, editability | – |
| preservation-api | overview, authentication, agents, repository | p01_overview/whoami.py, p02_authentication/get_token.py, p03_repository/*.py |

Everything else under `site/src/content/docs/` is a placeholder `overview.mdx`.
`preservation-docs-client/` has the shared helpers (`preservation.py`, `s3_helpers.py`,
`settings.py`, `example.env`); samples cannot be run yet against a hosted instance, but the local
stack runs (see below) so they can be exercised against `localhost` with `DISABLE_AUTH=true`.

Samples are run as modules from `preservation-docs-client/` (`python -m p03_repository.browse_repository`);
the `python dir/script.py` form cannot find `settings.py`.

Findings so far: `findings.md` (open: the Binary `content` URI is not served by the
Preservation API) and `findings-F.md` (METS: parser detects virus events by PREMIS eventType, not
ID prefix; judge PR #238 still open; code repo's CLAUDE.md is stale about where METS classes live —
they are in `DigitalPreservation.Mets`, not `Storage.Repository.Common`).

## How to work

- **One or two writing agents at a time.** Eight in parallel exhausted a whole session in nine
  minutes. Tom also wants to read each section as it lands. Opus is fine for the writing; keep the
  stronger model for reviewing findings and the judgement-heavy pages (authentication, editability,
  "where the Storage API differs").
- Every agent brief must say: read `CLAUDE.md` and `site-plan.md` first; verify everything against
  `C:\git\uol-dlip\digital-preservation\src\DigitalPreservation`; the code wins over the old docs;
  append discrepancies to `scratch/findings-<letter>.md`; do NOT run the build or commit; MDX
  gotchas (escape `{}` and `<` outside code spans; no HTML comments). After each agent: build,
  read the pages, merge its findings into `findings.md`, commit.
- Raw material is `documentation/02-Preservation-API.md` (1,710 lines; section line numbers below
  are approximate) and `06-Quickstart-preservation-workflow.md`. `playwright/PreservationApi/tests/`
  are old TypeScript exercises of the same flows. `src/mets-id-migration/app/api.py` in the code
  repo is a real, current Python client with good comments on API semantics.

## Remaining briefs, in order

### 1. preservation-api/authentication.mdx (order 2) — DONE (commit 18f2cfe)
Stance (in CLAUDE.md): bearer JWT via standard OAuth2 client-credentials from whichever identity
provider the instance is configured with; Entra ID is today's concrete example (token endpoint,
`api://<app-id>/.default` scope), not the design. Explain `X-Client-Identity` (what the API
records from it; the `source` values `user`/`token`/`header-fallback`/`unknown` on /whoami). UI
users sign in interactively. `FeatureFlags:DisableAuth` only as a local-dev note.
Verify in `Preservation.API/Program.cs`, `DigitalPreservation.Core` (AuthFilterIdentifier,
CallerResolver, IClientDirectory, depositBucket profiles from RFC-0001), `appsettings.Example.json`.
Don't invent roles you can't see.

### 2. preservation-api/deposits, deposit-files, editing-mets (orders 4, 5, 6)
Raw: 02 lines ~340–1015. Verify: `Features/Deposits/DepositsController.cs` (every route except
iiif*, pipeline*, archive-job) and `Requests/*`; `DepositQuery` (exact params incl. newer ones such
as `Archived`, whose semantics are commented in mets-id-migration's api.py); Common.Model `Deposit`
(all returned properties: pipelineJobs, archivalGroupExists, metsETag, lockedBy/lockDate, active,
archived…), `DeleteSelection`, `SchemaAndValue`, WorkingDirectory/WorkingFile/MetsExtensions and
every Metadata type (fill in the EXIF and virus-scan properties the old doc left "tbc");
`DigitalPreservation.Workspace/WorkspaceManager.cs` (add/delete-to-METS, METS location, ETag check
and the status code on mismatch); `LeedsDlipServices` (from-identifier schemas). Settle the old
WARNING about `deleteFromDepositFiles` vs `deleteFromMets` from the code. Document
`GET {id}/combined`, `GET {id}/parsed-mets`, `POST {id}/mets/normalise`, `PUT {id}/activate|deactivate`.
Samples: p04_deposits (create, get_and_patch, list, lock_unlock, delete, ensure_deposit helper),
p05_deposit_files (filesystem_view, combined_view), p06_editing_mets (add_files_to_mets, delete_from_mets).

### 3. preservation-api/import-jobs, import-job-results, exports + workflows/* (orders 8–10; workflows 1–8)
Raw: 02 lines ~1139–1407 and all of 06. Verify: `Features/ImportJobs/*` (diff generation; execute
incl. the diff-id-only body; belongs-to-deposit, isUpdate, sourceVersion and lock checks; activity
suppression flag), Common.Model ImportJob/ImportJobResult (JSON casing of the operation lists as
actually serialised; how renames are expressed), export route and METS-only export for an existing
AG, `Features/DepositArchiveJobs` and the `archived` flag (what the deposit archiver is, as a caller
sees it), Storage API result status strings, BagIt `data/` prefix in the diff.
Workflow pages as `Steps` walk-throughs: preserve-first-time, update-with-export,
update-without-export, custom-import-job, managed-mets-deposit, bagit-deposit,
reading-the-activity-stream (how-to; the stream reference lives in activity-stream.mdx).
Samples: p08_import_jobs, p09_import_job_results, p10_exports, and w02…w08 end-to-end scripts;
w02 needs a minimal METS with premis SHA256 fixity (see MetsParser for what it needs; a real one
is in playwright/PreservationApi/samples); tiny files in preservation-docs-client/sample_files/.

### 4. preservation-api/tool-outputs-and-pipelines (order 7) + internals/pipeline-api (order 3)
Undocumented today. Raw: 02 "Tool outputs and pipelines" (~1015–1135), rfcs/006 and 006a (intent
only). Verify: RunPipeline/RunPipelineStatus requests, `Features/PipelineRunJobs`, the SNS publish,
all of `Pipeline.API` (controller, runner, executor service, SQS/in-process queues, config, ApiKey
middleware, Dockerfile: Brunnhilde/Siegfried/ClamAV/ExifTool/BagIt), how tool outputs are read
(grep siegfried/brunnhilde/viruscheck/exif/manifest-sha256 in Workspace and Storage.Repository.Common
→ the definitive locations table), the ad-hoc metadata folder (MetadataAdHoc), job-claim
idempotency (#221). Sample: p07_pipelines/run_pipeline.py.

### 5. preservation-api/activity-stream, versions-and-storage-map, search, iiif, vocabularies (11–15)
Raw: 02 lines ~1408–1711. Verify: `Features/Activity` (incl. POST push: who and why; seeAlso
target — old WARNING says Storage API), `Features/Ocfl`, `Features/Search` (response shape),
`Features/Iiif`, deposit iiif / iiif-token routes and UpdateLogicalStructMapsFromManifest,
`Features/MediaServer`, the manifest builder, `AccessConditions` and `RangeTypes` controllers
(where the values come from). Samples: p11_activity_stream, p12_versions, p13_search, p14_iiif,
p15_vocabularies.

### 6. ui/* (orders 1–5)
No existing docs. Write from `DigitalPreservation.UI` (Pages/*.cshtml + .cs, Controllers, wwwroot
JS). Audience: staff users. Pages: overview, browsing, deposits (the big one: upload, folders, add
to METS, metadata/access conditions/inheritance, structure editing, pipeline, lock, activate,
archive), import-jobs, search-and-changes. Screenshot placeholders as `{/* screenshot: … */}`.
Note `FeatureFlags:ShowNormaliseMetsIds` gates the normalise action.

### 7. storage-api/* (1–4) + internals/overview, iiif-builder, deployment (1, 4, 5)
Raw: 03-Storage-API.md, 01-Introduction.md, code repo CLAUDE.md. Storage API only "where it
differs"; a same/differs table linking to the Preservation API pages. Verify `Storage.API/Features/*`
(content, import incl. test-path, export + export-mets-only, activity, storagemap, FedoraSearch),
`Storage.API.Importer`, `src/iiif-builder/app/*` (settings.py env vars, main loop), workflows and
docker-compose files, each `appsettings.Example.json` (section names only).
`internals/workspace-manager` is DEFERRED: short pointer page only (see site-plan.md).

## Follow-ups noted, not scheduled
- Fold `sequence-diagrams/` (Mermaid) into the site; retire the `gh-pages` branch and its Jekyll
  workflow once `docs-site` merges (Pages source is already "GitHub Actions"; last deploy wins).
- WorkspaceManager and the METS parser/object model will become standalone libraries (.NET and
  Python); document them separately when extracted.
- Update the code repo's CLAUDE.md about the `DigitalPreservation.Mets` project location.

## Local stack (for running samples)
`docker compose -f docker-compose.local.yml up -d db-preservation db-storage` in the code repo,
then `dotnet run` Storage.API (https://localhost:7000) and Preservation.API (https://localhost:7228)
from `src/DigitalPreservation`; Development settings point at the shared dev Fedora and the dev
deposits bucket with auth disabled. AWS profile `leeds` must be valid. `pip install boto3` is
still needed in the Python environment.
