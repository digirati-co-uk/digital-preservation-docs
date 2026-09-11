# Findings while porting the documentation

Discrepancies between the old documentation, the site, and the code, found while porting.
Each entry says where it was found, what the code actually does, and whether it looks like a
documentation error or a code bug.

## Open

- **Binary `content` URI is not served by the Preservation API.** (repository page) The old doc said
  `GET /content/...` on the Preservation API returns 403; there is no `/content` route in
  Preservation.API at all, so it is a 404. Only the Storage API serves it. Either add a proxying
  endpoint (with authorisation) or stop emitting a Preservation-API-hosted `content` URI on
  Binaries. Needs a decision.

## Resolved
