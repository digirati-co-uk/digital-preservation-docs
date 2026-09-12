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
