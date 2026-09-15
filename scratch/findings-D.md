# Findings while documenting the Preservation UI

From the agent that wrote `ui/*` from `DigitalPreservation.UI` (branch `feature/multiple-deposit-buckets`).
Items marked **[verified]** were re-checked directly; the rest are as reported and worth confirming
before acting on them.

## Corrected before filing

- **"Real credentials are committed in `DigitalPreservation.UI/appsettings.Development.json`" — NOT
  TRUE, and the correction matters.** The file does hold live-looking values (two 40-character Entra
  client secrets, the Identity Service and MVP Catalogue API keys), but it is **not committed and
  never has been**: `.gitignore:20` carries `appsettings.Development*`, `git ls-files` shows no
  tracked `appsettings.Development.json` anywhere in the repo, and the path has no history.
  **[verified]** It is an ordinary local developer config. No action; recorded so the claim is not
  repeated.

## Findings

Everything below is the record of what was found. Whether anything needs *doing* about it is
decided in `findings.md`, not here; most of these needed only the site to say the right thing, which
it now does.

- **Agent links go to a page that does not exist.** **[verified: no `Pages/Agents*` exists]**
  `TagHelpers/AgentLink.cs` renders every `createdBy`/`lastModifiedBy`/`preservedBy` as a link to
  `/agents/<slug>`. Nothing serves that route in the UI, so every one 404s. They appear throughout
  the Deposit side panel and the Browse footer. Code bug — add the page, or render a span. Note the
  Preservation API's own `agents.mdx` says Agent URIs are identifiers, not yet dereferenceable
  resources, so the UI is promising something the platform does not offer.

- **A display helper throws on data a third-party METS can produce.** **[verified: three
  `NotSupportedException` throws in `Pages/Shared/ModsMetadataDisplayBuilder.cs`, lines 57, 68, 84]**
  `GetDisplayItems` throws when an explicit value is present but the effective value differs, for
  access restrictions, rights statement and record identifiers. It is called from the Browse
  listing, the Binary view and every deposit file-table row, so one inconsistent item takes the
  whole page down with a 500 rather than degrading. The invariant holds for METS the platform wrote;
  `MetsParser` also reads METS it did not write. Should log and show the effective value.

- **Rendering the Deposit page performs writes, sync-over-async.** **[verified: two `.Result` calls
  at `Pages/Deposits/Deposit.cshtml.cs:720` and `:758`]** `GetCleanedPipelineJobsRunning()` runs on
  every GET, blocks on `GetPipelineJobResults().Result` twice (thread-pool starvation shape on a
  Razor Page), and for any pipeline job begun or queued more than `PipelineJobsCleanupMinutes`
  (default 1440) ago and not complete it releases the deposit's lock and POSTs
  `completedWithErrors` to the Preservation API — in a loop, with no cancellation token. The
  behaviour is useful (stuck deposits unstick themselves) and the site documents it as a note, but
  it belongs in a background job.

- **The Changes (activity stream) page is unreachable from the UI.** `Pages/Changes.cshtml` is
  routed at `/changes/{stream}/{index?}` and works, but nothing links to it — you have to type
  `/changes/archivalgroups`. Documented on the site as "type the address"; a link from the Archival
  Group page would be better.

- **Upload is documented in code as small-file-only, but nothing enforces it.** The handler is
  `WorkspaceManager.UploadSingleSmallFile` and `Deposit.cshtml.cs` says *"This is only for small
  files! one at a time."* Meanwhile `Program.cs` sets `Kestrel.Limits.MaxRequestBodySize` and
  `FormOptions.MultipartBodyLengthLimit` to `long.MaxValue`, and the only guard in `deposit.js` is a
  cosmetic warning above 2 GB. `hashFile()` does `file.arrayBuffer()` then `crypto.subtle.digest`,
  so the whole file is materialised in browser memory before anything is sent. The promise chain has
  no `.catch`, so on failure the Checksum box stays empty and the form posts anyway, giving "No
  checksum supplied in form". The site documents the warning and steers large uploads to S3 plus
  **Refresh storage**. Wants either a chunked upload or an explicit limit with a clear message.

- **Two feature flags for one feature.** `FeatureFlags:ShowNormaliseMetsIds` (UI) and
  `EnableMetsIdNormalisation` (API) must both be on; the UI's own comment says turning on the UI
  flag alone "shows a menu item that will be refused". The same UI flag also gates the "keep this
  version out of the Activity Stream" tick box — a separate capability whose only server-side guard
  is the check in `ImportJobModel.OnPostExecuteDiffDirect`. The coupling is invisible from
  configuration.

- **The IIIF button is gated on a hard-coded container name.** `BrowseModel.OnGet` sets
  `HasPredictableIIIFPath = parentSlug is "cc" or "cc-test"`, above a `// Temporary` comment. Every
  other Archival Group gets a permanently disabled button with no explanation.

- **The diff button's guard is carried in `TempData`.** `BindDeposit` writes
  `TempData["MisMatchCount"]`; `Deposit.cshtml` both reads it (banner) and tests it (disabling
  **Create diff import job**), and several POST handlers call `TempData.Remove(...)` to compensate.
  `TempData` is a read-once, request-surviving store; a page-model field would be correct and
  simpler. No failure observed, but the site documents the disabling as a rule.

- **Dead sidebar entries and template furniture.** `_Layout.cshtml` still carries the Bootstrap
  dashboard sample's nav: **Reports** (`/reports`) and **Integrations** (`/integrations`) route
  nowhere, "Saved reports" links to `#`, and the mobile offcanvas is titled "Company name". The
  Dashboard, Status and Error pages each carry non-functional **Share**/**Export** buttons and a
  "This week" dropdown. **Settings** goes to `/status`, whose heading is "Connectivity Checks".

- **Stub UI on the Import Job page.** A toolbar button labelled **Something** with a trash icon and
  no handler, and a permanently disabled "Run modified import" form under *"UI to follow"*.

- **A developer-facing message can reach users.** When the deposits query fails,
  `Pages/Deposits/Index.cshtml` renders *"No PagerValues Present - are any deposits returned?"*.

- **Dead partial: `Pages/Deposits/_RenderDirectory.cshtml`** — its only reference is to itself.

## Consistent with the API documentation (checked, no action)

- **Delete offers no "METS only" option**, matching the caution in `editing-mets.mdx`: the radios
  map to `Whereabouts.Deposit` and `Whereabouts.Both`. `Whereabouts.Mets` is handled in
  `OnPostDeleteItems` but never offered.
- **Deactivate is only offered when status is `error`**, matching `deposits.mdx` — rendered inside
  an `@if` on that status, so the UI never asks for the 400.
- **The Binary "Content" link is marked as unavailable in the UI itself**, corroborating the open
  finding in `findings.md` that `content` is not served by the Preservation API. `BinaryController`
  at `/binary/{*path}` proxies `GetContentStream`, but nothing links to it.
- **Rights inheritance: an explicitly empty rights element stops inheritance.** Checked against
  `MetsParser`, `RightsStatement.DoNotInheritSentinel`, and
  `digital-preservation/docs/effective-metadata-inheritance.md`. Doc and code agree; the UI exposes
  it as *(inherit from parent)* vs *(none — do not inherit)*.

## Could not be determined from the code

- Whether `/reports`, `/integrations` and "Saved reports" are planned or abandoned (documented as
  not implemented).
- What the IIIF button's `cc` / `cc-test` gate will become — the code says `// Temporary`.
- Which `stream` names `/changes/{stream}` accepts besides `archivalgroups`.
