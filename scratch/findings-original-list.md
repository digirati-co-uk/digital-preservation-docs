# Findings while porting the documentation

Discrepancies between the old documentation, the site, and the code, found while porting.
Each entry says where it was found, what the code actually does, and whether it looks like a
documentation error or a code bug.

## Open

- **The site documents RFC-0001 Phase 0 code that is not yet on `main`.** (overview, authentication)
  `/whoami`, `CallerResolver`, `WhoAmIResult`, `IClientDirectory`/`KnownClients` and the per-caller
  `depositBucket` routing exist only on the code repo's `feature/multiple-deposit-buckets` branch;
  `origin/main` has just `AuthFilterIdentifier` and `ClaimsPrincipalX`. The overview page (previous
  session) and the authentication page both describe the branch. That matches the handover's
  instruction to verify against the working tree, and Tom has confirmed the direction, but the site
  must not go live describing endpoints a deployed instance does not have. Check before publishing;
  and once `docs/rfc-0001-api-caller-identity.md` reaches `main`, link it from the authentication
  page's "transitional arrangement" note (deliberately unlinked for now — it would 404).

- **`MetsExtensions` property names: the old doc says `physDivId`, the code says `divId`.**
  (deposit-files page) `DigitalPreservation.Common.Model/Transit/Extensions/MetsExtensions.cs`
  serialises `href`, `divId` and `admId`. The old doc's table names `physDivId` and `admId` and
  omits `href` entirely. Documentation error; the site uses the real names.

- **The Deposit resource has no `pipelineJobs` property.** (deposits page) The example Deposit in
  `documentation/02-Preservation-API.md` includes `"pipelineJobs": []`, but nothing in
  `Common.Model.PreservationApi.Deposit` produces it. Pipeline job results are a separate
  endpoint, `GET /deposits/{id}/pipelinerunjobs`. Documentation error.

- **Lock conflicts are reported as 401 by some operations and 409 by others.** (editing-mets page)
  `WorkspaceManager.AddItemsToMets`, `DeleteItems` and `CreateFolder` return
  `ErrorCodes.Unauthorized` when another caller holds the lock, which `ResultX.ToProblemDetails`
  maps to **401**. The controller-level checks for the same condition (patch, delete, normalise)
  return `Conflict` → **409**. Same situation, two status codes, and 401 is misleading: the caller
  is authenticated and authorised, the deposit is busy. Looks like a code bug; the site documents
  the behaviour as it is.

- **`DeleteSelection.ContinueIfFail` reads as the opposite of what it does.** (editing-mets page)
  In `DeleteItems`, a failure is swallowed and the item recorded as deleted when the list is
  non-empty and does NOT contain that item's path; a failure on a path that IS in the list aborts
  the whole operation. So the list names the paths whose failure is fatal, while the name says the
  reverse. Only caller is `ExecutePipelineJob` (pipeline metadata folders). The property is also
  the only one on `DeleteSelection` without an explicit `JsonPropertyName`. Undocumented on the
  site deliberately; worth renaming or inverting in code.

- **`ExifTag.mismatchAdded` is serialised to API clients.** (deposit-files page) It is internal
  bookkeeping for mismatch generation between deposit and METS EXIF, mutated during comparison,
  but it is a public property with a `JsonPropertyName` and so appears in the file system view.
  Harmless, confusing; left out of the documented table.

- **`ExifTagComparer.GetHashCode` is inverted.** (deposit-files page)
  `!string.IsNullOrEmpty(exifTag.TagName) ? 0 : exifTag.TagName?.GetHashCode() ?? 0` returns 0 for
  every non-empty value, so every tag hashes to 0 and the `Except`/`SequenceEqual` calls that use
  the comparer degrade to O(n²). Results are still correct because `Equals` is right. Code bug,
  performance only.

- **`DepositQuery.ShowForm` is a UI property on a shared API class.** (deposits page) No API
  handler reads it — `GetDepositsHandler` ignores it and `NoTerms()` does not consider it — so as an
  API query parameter it does nothing. It is not dead, though: `DigitalPreservation.UI`
  `Pages/Deposits/Index.cshtml:14` reads `Model.Query.ShowForm` to remember whether the advanced
  search panel is open, which is why `/deposits?showForm=true` appears in UI URLs. Confirmed in the
  running dev UI. Deliberately undocumented as an API parameter; noted here so it is not mistaken
  for dead code and removed.

- **The site assumes S3 as the Deposit backing store, which will not always be true.**
  (deposits, deposit-files) Tom: S3 is the only valid back end at the moment, but the intention is
  to support a file share or local drive too — `file:///` URIs alongside `s3://`. There is already
  a file-system implementation of the METS loader/storage (`DigitalPreservation.Mets/StorageImpl/
  FileSystemMetsLoader.cs`, `FileSystemMetsStorage.cs`) next to the S3 one. Decision taken for now:
  write S3 concretely rather than abstracting it. **When a second backing store lands, the
  deposits and deposit-files pages (and the samples' `s3_helpers.py`) need revisiting** so a
  workspace on a mounted drive is a first-class case.

- **Binary `content` URI is not served by the Preservation API.** (repository page) The old doc said
  `GET /content/...` on the Preservation API returns 403; there is no `/content` route in
  Preservation.API at all, so it is a 404. Only the Storage API serves it. Either add a proxying
  endpoint (with authorisation) or stop emitting a Preservation-API-hosted `content` URI on
  Binaries. Needs a decision.

- **`Storage.API/appsettings.Example.json` ships `FeatureFlags:DisableAuth` as `"true"`.**
  (authentication page) Anyone following the documented "start from `appsettings.Example.json`"
  advice for the Storage API gets an API with authentication switched off — the flag skips the
  whole filter stack (`AuthorizeFilter` and `AuthFilterIdentifier`) and `UseAuthentication()`.
  `Preservation.API`'s example ships `"false"`, correctly. Already noted in RFC-0001 §7 and still
  true. Looks like a code/config bug: the example should default to secure.

- **`FeatureFlags:DisableAuth` does nothing in Pipeline API.** (authentication page, internals)
  `Pipeline.API/appsettings.json`, `.Development.json`, `.Example.json` and `.Testing.json` all set
  it to `"true"`, but no code in `Pipeline.API` reads it — only Preservation API, Storage API and
  the Importer do. Pipeline API authenticates with `X-API-KEY` unconditionally. Harmless but
  misleading dead config; the code repo's CLAUDE.md also says the flag "disables all auth for local
  development", which is not true of Pipeline API.

- **Old doc: client credentials with "Refresh Tokens".** (authentication page)
  `documentation/02-Preservation-API.md` §Authentication says the API implements the client
  credentials flow "with Refresh Tokens to ensure that access tokens are short lived and can be
  revoked". The client-credentials grant does not issue refresh tokens (RFC 6749 §4.4.3): a client
  simply requests a new token when the old one expires. Documentation error; the site keeps the
  intent (short-lived, revocable) without the refresh-token claim.

- **The Python samples could not be run as documented.** (samples)
  `preservation-docs-client/README.md` said `python p02_repository/browse_repository.py` — wrong
  directory number, and that form fails with `ModuleNotFoundError: No module named 'settings'`,
  because Python puts the *script's* directory on `sys.path`, not the client root. Fixed in the
  README: run them as modules from the client root (`python -m p03_repository.browse_repository`).

## Resolved
