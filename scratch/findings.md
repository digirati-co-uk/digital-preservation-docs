# Findings

What the documentation port turned up, and what - if anything - to do about each thing.

Around 150 findings were recorded across the `findings-*.md` files while the site was written.
Most needed nothing beyond the site saying the right thing, which it now does. This page sorts the
rest by what they need: a decision, an issue that now exists, or a note to come back when something
else happens. If it is not on this page, it needs no action.

Everything here was checked against the code. Items marked **[live]** were also measured against the
development instance.

## Nothing to do

About two thirds of the findings are errors in the *old* markdown - wrong property names, wrong
casing, wrong paths, examples that never matched the code - recorded so that anyone comparing the
old pages with the site can see why they differ. The site is right, the old pages carry banners, and
that is the end of it. They stay in the detail files as the record; they are not repeated here.

A further handful are code observations that are true and harmless: dead configuration, unused
properties, a comparer with a bad hash. Those are listed under "Dead or misleading code" at the
bottom, as a shopping list for whoever next has a tidy-up afternoon, not as work.

## Needs a decision

Three things where the right answer is not obvious and a patch would be guessing.

- **The `content` URI on a Binary.** The Preservation API emits a `content` URI on its own host
  that it does not serve (there is no `/content` route; it 404s), and the Storage API's version
  ignores `?version=`. Either the Preservation API proxies content, with authorisation, or it stops
  emitting the URI. Part of #265, but the other two leaks in that issue are mechanical and this one
  is not. (findings-original-list, findings-E)

- **Who locks the deposit for a pipeline run.** RFC 006a says the Preservation API locks the deposit
  as the pipeline user. It does not: `POST /deposits/{id}/pipeline` checks nobody *else* holds the
  lock and queues the job, the UI takes the lock itself beforehand, and the Pipeline API releases
  the lock at the end whether or not it took it. So an API caller who does not lock first has no
  protection during the run, and one who does has the lock taken away. The lock ought to be
  acquired by whatever queues the job. Documented as it is on `tool-outputs-and-pipelines`.
  (findings-B)

- **The IIIF deposit token lives in one process's memory.** The tokenised `/media/...` routes are
  anonymous, and the token is held in the API's in-process `IMemoryCache`. It dies on restart and
  does not work across more than one API instance behind a load balancer. That is a deployment
  constraint on a feature that is off by default (`EnableIiifMediaEndpoints`), so it may not matter
  yet - but it decides whether the feature can ever be turned on in production as built. Belongs
  with #261. (findings-C)

Two that were on this list have come off it: `DisableAuth` in the Storage API example config was
never a decision and is fixed (PR #270); whether a hand-written Import Job may name a different
Archival Group is settled - it may not (PR #271, closes #267).

## Raised as issues

All on the code repository. Nothing is outstanding in the documentation for any of these: each is
described on the site as the platform currently behaves. **When one closes, the page named needs
its note taken out** - only #262 links its issue, so the map is here.

| # | What | Site page to revisit when it closes |
|---|---|---|
| [#258](https://github.com/digirati-co-uk/digital-preservation/issues/258) | Lock conflicts answer 401 from some operations and 409 from others | `preservation-api/editing-mets` |
| [#259](https://github.com/digirati-co-uk/digital-preservation/issues/259) | `DeleteSelection.ContinueIfFail` has inverted logic | none - deliberately undocumented |
| [#260](https://github.com/digirati-co-uk/digital-preservation/issues/260) | Import jobs accept renames and never perform them | `preservation-api/import-jobs`, `storage-api/import` |
| [#262](https://github.com/digirati-co-uk/digital-preservation/issues/262) | Storage API `/content` returns HTTP 200 with a body saying 404 | `storage-api/activity-and-content` (linked) |
| [#263](https://github.com/digirati-co-uk/digital-preservation/issues/263) | `archived`/`active` silently ignored; agent filters reject Agent URIs **[live]** | `preservation-api/deposits`, `preservation-api/agents` |
| [#264](https://github.com/digirati-co-uk/digital-preservation/issues/264) | `metsETag` absent from the create response and from listings **[live]** | `preservation-api/deposits`, `editing-mets`, `introduction/quickstart`; samples `ensure_deposit.py`, `ready_deposit.py` |
| [#265](https://github.com/digirati-co-uk/digital-preservation/issues/265) | Storage API URIs leak into Preservation responses (`seeAlso`, `importJob`, `content`) | `preservation-api/activity-stream`, `import-job-results`, `repository` |
| [#266](https://github.com/digirati-co-uk/digital-preservation/issues/266) | Caller errors surfacing as HTTP 500 (`PreconditionFailed`, non-head export) | `preservation-api/exports`, `editing-mets` |
| [#268](https://github.com/digirati-co-uk/digital-preservation/issues/268) | UI: agent links 404, a display helper throws, inherited metadata invisible until hover, a GET performs writes | `ui/deposits`, `ui/browsing` |
| [#269](https://github.com/digirati-co-uk/digital-preservation/issues/269) | The first published activity is an unsuppressed seed row pointing at `example.com` | `preservation-api/activity-stream`, `workflows/reading-the-activity-stream` |

Closed: [#267](https://github.com/digirati-co-uk/digital-preservation/issues/267) (Archival Group
check, PR #271). Fixed without an issue: `Storage.API/appsettings.Example.json` shipping
`DisableAuth: "true"` (PR #270).

## Code bugs found during the port, filed 2026-09-15

Everything the detail files recorded as a code defect and had not been filed is now an issue, one
per service, except the one that was significant enough to stand alone. Each issue says which
detail file it came from; the detail files are not repeated here.

| # | What | Site page to revisit when it closes |
|---|---|---|
| [#272](https://github.com/digirati-co-uk/digital-preservation/issues/272) | Storage API: `GET /FedoraSearch` with no `pageSize` runs an unbounded query (a denial-of-service shape; on its own for that reason) | `storage-api/activity-and-content` |
| [#273](https://github.com/digirati-co-uk/digital-preservation/issues/273) | Storage API: `createdBy` null dereference on import; `exportMetsOnly` failure is a 500; Exports stored without `created`/`createdBy`; activity stream objects typed `ImportJob` and never `Create` | `storage-api/import`, `storage-api/export`, `storage-api/activity-and-content` |
| [#274](https://github.com/digirati-co-uk/digital-preservation/issues/274) | Preservation API: diff-reference match is case-sensitive; rename lists have no `JsonPropertyName`; search echoes null `text`/`searchType`; `/deposits/{id}/iiif` redirects into a 401 | `preservation-api/import-jobs`, `search`, `iiif` |
| [#275](https://github.com/digirati-co-uk/digital-preservation/issues/275) | Pipeline API: upload guard passes by coincidence; `ApiKeyAttribute` fails open | none |
| [#276](https://github.com/digirati-co-uk/digital-preservation/issues/276) | Preservation UI: everything not in #268 - no upload limit, IIIF button hard-coded to `cc`, `TempData` guard, unlinked Changes page, coupled feature flags, template furniture, BagIt edge cases | `ui/deposits`, `ui/browsing` |
| [#277](https://github.com/digirati-co-uk/digital-preservation/issues/277) | `deploy.yml` retags the deposit-archiver image but never deploys it | none |

Not filed, on purpose: the two Pipeline API items already in the April 2026 security review (path
traversal in the diagnostics endpoint, non-constant-time API key comparison) stay tracked there
rather than being restated in a public issue; and the two iiif-builder defects (`lstrip` where
`removeprefix` is meant; the table created by hand), because Leeds run their own fork and the copy
in this repository is deliberately undocumented. Both are in `findings-E.md` if that changes.

## Come back to these when something else happens

Documentation follow-ups that are correct today and will stop being correct on a known trigger.

| When | Do |
|---|---|
| PR #238 (editability judge) merges | `mets/editability` says the judge is designed, not shipped, and links the PR; flip it. RFC 008 on the docs repo links the judge on the branch - point it at `main`. (findings-F) |
| The production METS-ID migration completes | `mets/identifiers` and the 02d banner: the mixed-form rules stop being load-bearing and the two legacy fallbacks named on the identifiers page become removable. (findings-F) |
| `docs/rfc-0001-api-caller-identity.md` reaches `main` on the code repo | Link it from the "transitional arrangement" note on `preservation-api/authentication`; left unlinked because it would 404. Not on `main` as of 2026-09-15. (findings-original-list) |
| A second deposit backing store lands (`file:///` workspaces) | `preservation-api/deposits`, `deposit-files` and the samples' `s3_helpers.py` all assume S3; a mounted drive needs to be a first-class case. Tom's decision was to write S3 concretely until then. (findings-original-list) |
| The IIIF endpoints move on (#261) | `preservation-api/iiif` is framed as experimental scaffolding; reframe when the paintedResources / access-conditions-to-roles work exists. |
| Any issue in the table above closes | Take the "as it is today" note out of the page named. |

## The code repo's own docs

`CLAUDE.md` on the code repository was wrong in four places found while writing the internals
pages: six ECR images not five; `docker compose up` not running the stack; the METS classes living
in `DigitalPreservation.Mets`; and `DisableAuth` doing nothing in Pipeline API. **Corrected in
[PR #278](https://github.com/digirati-co-uk/digital-preservation/pull/278).**

Still stale, not worth a PR of its own: `clamscan-shim.sh`'s header comment describes a socket
bind-mounted from the host, but `clamd` runs inside the container. (findings-B)

## Dead or misleading code, not worth an issue each

- `FeatureFlags:UseLocalHostedServiceForPipeline` is read by nothing: `Program.cs` registers
  `SqsPipelineQueue` last, so it always wins and `InProcessPipelineQueue` is unreachable. Running
  Pipeline API locally without AWS is therefore not possible as wired.
- `FeatureFlags:DisableAuth` is set in four `Pipeline.API` settings files and read by none of them.
- `ProcessPipelineResult.virusDefinition` and `cleanupProcessJob` are serialised but never populated.
- `ArchiveJobResult` always has `id` and `status` null - the only API resource with no `id`.
- `ExifTagComparer.GetHashCode` is inverted, so every tag hashes to 0 and the comparisons that use it
  degrade to O(n squared). Results stay correct.
- `ExifTag.mismatchAdded` is internal bookkeeping but is serialised to API clients.
- `DepositQuery.ShowForm` does nothing in the API - but it is **not** dead: the UI reads it to
  remember whether the advanced search panel is open.
- `Pages/Deposits/_RenderDirectory.cshtml` is referenced only by itself.
- The Deposit `template` is never persisted, so every response says `"template": "None"` whatever was
  asked for. **[live]**
- `AccessRestriction.All` is a static list nothing reads; the vocabulary comes from configuration.
- `GET /import/test-path/...` returns an empty `ArchivalGroup` whatever it found; only the status
  code means anything.
- `FeatureFlags:UseLocalHostedServiceForExport` has exactly one valid value: `false` makes the
  Storage API refuse to start.
- Storage API `createdBy`/`lastModifiedBy` URIs are minted on the Storage host, which has no
  `/agents` route; the Preservation API's mutator happens to rewrite them onto a host where they
  resolve.

## The originals are still misleading, and Leeds may read them

Each file in `documentation/` now carries a banner pointing at its replacement. The three worth
knowing about:

- **02c's virus-scan rule is stale.** It says the parser takes the last `digiprovMD` whose ID starts
  with `digiprovMD_ClamAV_`. It matches `premis:eventType` = `virus check`; the prefix is only a
  fallback. Third-party provenance declaring itself a virus check is in scope, where the old rule
  implies it is not.
- **02e reads as though the editability judge exists.** PR #238 is still open; the shipped rule is
  the `mets:agent` name check.
- **02d says the migration campaigns have not run.** Development has since completed.

## Where the detail is

| File | What it covers |
|---|---|
| `findings-original-list.md` | The first entries, from porting the overview and repository pages |
| `findings-A.md` | Import jobs, results, exports, the workflow pages |
| `findings-B.md` | Tool outputs and the Pipeline API |
| `findings-C.md` | Activity stream, versions, search, IIIF, vocabularies |
| `findings-D.md` | The Preservation UI |
| `findings-E.md` | Storage API and the internals pages |
| `findings-F.md` | METS (the 02a-02e port), from the first session |
| `findings-V-verification.md` | The two verification passes over the finished pages |
| `review-2026-09-13.md` | The review of the finished port |

The detail files each open with a section headed "Findings". It used to say "Open", which read as
"awaiting action" when it meant "not yet sorted into this index"; hence this page.

## One for whoever writes here next

Three of the four broken sequences the verification pass found were in `workflows/recipes.mdx`,
written quickly from memory rather than checked against the code - including a
`GET /repository/{path}/versions` route that has never existed. Short snippets need the same
verification as long ones, and arguably more, because they are what people copy.
