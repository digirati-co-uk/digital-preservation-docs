# Findings from the verification pass

(Was briefly written to `findings-F.md` by mistake, overwriting the METS findings from the
previous session; those are restored and this is the verification pass's own file.)

A checking agent re-read twenty-three committed pages against the code and found seventeen errors.
All of them have been corrected on the site. What follows is the residue: the things that are wrong
in the **code**, or that a reader should know, rather than things that were wrong in the prose.

Four were confirmed against the running dev instance, marked **[live]**.

## Code bugs the verification turned up

- **`ErrorCodes.PreconditionFailed` maps to 500.** `ResultX.ToProblemDetails`
  (`DigitalPreservation.Core/Web/ResultX.cs:11-34`) has cases for NotFound, Unauthorized,
  BadRequest, Conflict, Unprocessable and Tombstone, and a `default` of 500. `PreconditionFailed` is
  defined in `ErrorCodes` but has no case, so an ETag failure raised down in storage
  (`S3MetsStorage.cs:50,94`) reaches the caller as **500**, not 412. The controller-level `If-Match`
  checks answer 409 and are unaffected. The site now documents 409 and no longer mentions 412.

- **`archived` and `active` are ignored unless another query term is present. [live]**
  `DepositQuery.NoTerms()` does not consider either property, so `GET /deposits?archived=true` takes
  the no-terms branch in `GetDeposits.cs:30-37` and returns `Where(d => d.Active)` — the default
  listing. Measured against dev: `?archived=true` returned 223 deposits whose first row had
  `archived: null` and status `new`; `?archived=true&showAll=true` returned 4,713, correctly
  archived. No error, no indication the filter was dropped. The page now carries a danger note.

- **The `createdBy`/`preservedBy`/`exportedBy` filters reject the very URIs `GET /agents` hands
  out. [live]** `GetDeposits.cs` compares with `==` against a column holding the bare caller name.
  `ResourceMutator.GetCallerIdentity(Uri)` exists at `:147` to convert a URI back to a name and is
  **never called**. Measured against dev: filtering by the full Agent URI returned 0, by the bare
  name returned 1, and by a prefix of the name returned 0. `agents.mdx` had been telling readers to
  use the `/agents` list for exactly this; both pages are corrected.

- **The Deposit `template` is never echoed back. [live]** It is not persisted and
  `ResourceMutator.MutateDeposit` never sets it, so every response says `"template": "None"`.
  Confirmed on a deposit created as `RootLevel`. Harmless but confusing; noted in the example.

- **Inherited metadata in the deposit file table is invisible until hover.**
  `wwwroot/css/site.css:334-343` gives `.dep-meta-inherited` `opacity: 0`, revealed only on
  `.deposit-row:hover` / `:focus-within`. So a blank metadata cell means "nothing set *here*", not
  "no value" — and the value cannot be seen by anyone not using a pointer. Worth treating as an
  accessibility bug as well as a usability one. The UI pages now say so.

- **`ImportJobResult.importJob` points at the Storage API host.** `MutateStorageBaseUris` rewrites
  `Id`, `CreatedBy` and `LastModifiedBy` but not `ImportJob`. Same family as the `seeAlso` problem
  in `findings-C.md` and the `content` URI problem in `findings.md`: Storage URIs leaking into
  Preservation API responses that most callers cannot dereference.

- **"You can only export the HEAD version" returns 500.** `CreateDepositBase.cs` uses
  `ErrorCodes.UnknownError` for what is a caller error; it should be 400 or 409.

- **`ArchiveJobResult` has no `id` and no `status`** — `MutateDepositArchiveJob` sets neither. The
  only API resource without an `id`.

## Corrected in the prose, no code change needed

- `ImportJob` and `ImportJobResult` **do** carry `lastModified`/`lastModifiedBy`: both extend
  `Resource`, and both are populated on write. The overview page had claimed otherwise.
- The Storage API is not wholly innocent of METS: `POST /exportmetsonly` selects files with
  `MetsUtils.IsMetsFile`, and `CreateDepositBase` relies on it. It recognises a METS file by name; it
  does not parse one.
- The Pipeline API, not the Preservation API, writes tool results into the METS.
- The Storage API talks to the Fedora database directly, read-only
  (`GetPopulatedContainer`, `GetSimpleSearch`, `GetSearchCount`), for containment listings and
  search. The architecture diagrams omitted this edge.
- An Archival Group Name is needed only when the import job *creates* the object, and it is the
  Storage API that refuses at execution — so the job reports `completedWithErrors` rather than
  failing up front.
- There is no Export resource on the Preservation API; you poll the Deposit, and polling is what
  moves it from `exporting` to `new`.

## Still uncertain

- Whether Fedora's `simple_search` half of the search is case-insensitive (the Deposit half
  demonstrably is). `Storage.API/Fedora/FedoraDB.cs:142` would settle it.
- Several BagIt edge cases in the UI look wrong for a `data/`-rooted deposit — the METS-row
  exemption in `_RenderCombinedDirectoryAsTableRows.cshtml:104`, `PathIsKnownFirstLevelDirectory`
  matching only bare `objects`/`metadata`, and `PhysicalFilePathsJson` filtering on
  `StartsWith("objects/")`. These read as code bugs; a real BagIt deposit would confirm.
- `Browse.cshtml.cs:83` only looks for not-yet-existing objects when the path has more than two
  segments, so they never appear at or just below the root. Unclear whether that is deliberate.

## Second verification pass (the 22 pages the first pass did not cover)

Three agents; 20 errors and 4 broken sequences, all corrected on the site. The residue:

- **`ContentController` returns HTTP 200 with a ProblemDetails body.** `new ObjectResult(pd)` with
  no `StatusCode`, twice, where the rest of the codebase uses `ControllerX.GetProblemObjectResult`
  which sets it. So a request for the bytes of something that is not a Binary answers 200 with JSON
  saying 404. Filed as [#262](https://github.com/digirati-co-uk/digital-preservation/issues/262).
  **[verified]**

- **A pipeline run writes the METS itself.** `ExecutePipelineJob` calls `AddObjectsToMets`
  unconditionally once the tools finish (`:571`), adding every file under `objects/`, and each
  Brunnhilde output is added as it is uploaded (`UploadFileToDeposit`, `updateMets` defaulting true).
  Three pages said the opposite — that tool output never reaches METS until you ask. True for output
  you place yourself, false for a platform pipeline run. **[verified]**

- **The Deposit `template` is never persisted**, so every response says `"template": "None"` whatever
  you asked for. Already recorded above; the second pass found it independently, and it means any
  example showing a `RootLevel` or `BagIt` deposit's response body would be wrong.

- **Several documented "requirements" on a hand-written Import Job are not enforced.**
  `ImportJob.ItemsWithInvalidSlugs()` and `AddedBinariesWithInvalidContentTypes()` exist but are
  called only by the UI. On the API path the only checks are a null `id` and a `#` in one. And
  `archivalGroup` is never compared with the Deposit's own — a job naming a different Archival Group
  runs against that group and reports success. That last one is worth a code fix.

- **A non-export Deposit against an Archival Group that has a METS always gets that METS copied in**,
  regardless of `template`. `None` suppresses writing a *new* METS, not copying the existing one.
  Three pages implied an empty workspace.

- **`POST /export` cannot report a version mismatch.** The 201 has already gone out; the conflict is
  only logged, so the Export never gains `dateFinished` and never gains an `errors` entry. Only the
  synchronous `exportMetsOnly` can answer 409.

- **`GET /repository/{path}` with `?version=vN` is Archival-Group-only** — a Container or Binary is a
  400 telling you to use the Memento timestamp.

- **Push to the activity stream**: a path that does not exist is 404 (410 if tombstoned), not the 400
  the page claimed; only a wrong resource *type* is 400.

Lesson for whoever writes here next: three of the four broken sequences were in `recipes.mdx`,
written quickly from memory rather than checked against the code — including a `GET
/repository/{path}/versions` route that has never existed. Short snippets need the same verification
as long ones, and arguably more, because they are what people copy.
