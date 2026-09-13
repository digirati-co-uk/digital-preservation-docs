# Findings

What the documentation port turned up. Around 150 individual findings were recorded across the
`findings-*.md` files while the site was written; this page is the index and the priority order.

Everything here was checked against the code. Items marked **[live]** were also measured against the
development instance.

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

## Raised as issues

All filed on the code repository. None of these is outstanding in the documentation: each is
described on the site as the platform currently behaves, with a note that comes out when the issue
is closed.

| # | What | Why it matters |
|---|---|---|
| [#258](https://github.com/digirati-co-uk/digital-preservation/issues/258) | Lock conflicts answer 401 from some operations and 409 from others | 401 makes a client refresh its token and retry forever |
| [#259](https://github.com/digirati-co-uk/digital-preservation/issues/259) | `DeleteSelection.ContinueIfFail` has inverted logic | A tolerated failure is reported as a deletion; the pipeline's own clean-up may be half-failing |
| [#260](https://github.com/digirati-co-uk/digital-preservation/issues/260) | Import jobs accept renames and never perform them | The job reports `completed` having changed nothing |
| [#262](https://github.com/digirati-co-uk/digital-preservation/issues/262) | Storage API `/content` returns HTTP 200 with a body saying 404 | The one endpoint serving raw bytes, where a wrong status is hardest to notice |
| [#263](https://github.com/digirati-co-uk/digital-preservation/issues/263) | `archived`/`active` silently ignored; agent filters reject Agent URIs **[live]** | `?archived=true` returns the ordinary active list; `GET /agents` output does not work as a filter |
| [#264](https://github.com/digirati-co-uk/digital-preservation/issues/264) | `metsETag` absent from the create response and from listings **[live]** | Four sample programs hit this independently; the resulting 409 points at the wrong thing |
| [#265](https://github.com/digirati-co-uk/digital-preservation/issues/265) | Storage API URIs leak into Preservation responses (`seeAlso`, `importJob`, `content`) | Callers are handed hosts they cannot reach |
| [#266](https://github.com/digirati-co-uk/digital-preservation/issues/266) | Caller errors surfacing as HTTP 500 (`PreconditionFailed`, non-head export) | |
| [#267](https://github.com/digirati-co-uk/digital-preservation/issues/267) | A hand-written Import Job can name a different Archival Group, and runs against it | Content lands in the wrong object and reports success. Becomes a security boundary once RFC-0001's per-caller roles land - see the comment on the issue |
| [#268](https://github.com/digirati-co-uk/digital-preservation/issues/268) | UI: agent links 404, a display helper throws on third-party METS, inherited metadata invisible until hover, a GET performs writes | |
| [#269](https://github.com/digirati-co-uk/digital-preservation/issues/269) | The first published activity is an unsuppressed seed row pointing at `example.com` | Every unattended consumer of the stream trips on page 1 |

## Needs a decision, not a patch

- **The `content` URI on a Binary.** Either the Preservation API proxies content, with
  authorisation, or it stops emitting a URI on its own host that it does not serve. Part of #265;
  the other two in that issue are mechanical, this one is not.
- **Whether the documented-but-unenforced Import Job requirements should be enforced** -
  `contentType` and slug validity, whose checks exist but are called only by the UI (#267).
- ~~`FeatureFlags:DisableAuth` in `Storage.API/appsettings.Example.json`~~ - moved to "just fix it"
  below; it was never a decision.

## Just fix it

- **`Storage.API/appsettings.Example.json` ships `FeatureFlags:DisableAuth` as `"true"`.** Change it
  to `"false"`. Anyone following "start from the example file" otherwise gets an unauthenticated
  Storage API - the one service that can write to Fedora - in a public repository whose docs tell
  people to start from the example file. One character; needs a PR, not a discussion.

## Dead or misleading code, not worth an issue each

- `FeatureFlags:UseLocalHostedServiceForPipeline` is read by nothing: `Program.cs` registers
  `SqsPipelineQueue` last, so it always wins and `InProcessPipelineQueue` is unreachable.
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
  asked for.

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

## One for whoever writes here next

Three of the four broken sequences the verification pass found were in `workflows/recipes.mdx`,
written quickly from memory rather than checked against the code - including a
`GET /repository/{path}/versions` route that has never existed. Short snippets need the same
verification as long ones, and arguably more, because they are what people copy.
