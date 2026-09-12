# Digital Preservation documentation

This repository holds the documentation for the Digital Preservation platform
(Preservation API, Storage API, Preservation UI, Pipeline API, iiif-builder), whose source is
at https://github.com/digirati-co-uk/digital-preservation (locally `C:\git\uol-dlip\digital-preservation`).

Layout:

- `site/` — the Astro + Starlight documentation website, deployed to GitHub Pages by
  `.github/workflows/deploy-site.yml`. Content lives in `site/src/content/docs/`.
- `preservation-docs-client/` — runnable Python samples that accompany the API pages.
- `documentation/` — the ORIGINAL markdown documentation. This is the raw material being ported
  into `site/`. It is out of date in places; do not link to it from the site. Once a page is
  fully ported and verified, its content in `documentation/` is superseded.
- `internals/` — how the platform is built, deployed and run. CURRENT documentation, deliberately
  not on the site: a different audience (people who run the platform) and a different rate of
  change. Plain markdown, not checked by the build.
- `rfcs/`, `adr/`, `sequence-diagrams/`, `schema/` — design history. Not part of the site
  (may be linked to on GitHub where useful).
- `playwright/` — older TypeScript API exercises. Useful as evidence of how the API behaves.
- `scratch/` — notes about features described in the old docs but not (yet) implemented, and
  open questions found while porting. Not published.

## Site development

```bash
cd site
npm install
npm run dev      # http://localhost:4321/digital-preservation-docs
npm run build    # must pass with no broken-link warnings before committing content
```

## Documentation principles

1. **Everything on the site must be true of the code as it is now.** Every endpoint, property,
   query parameter, status code and state value must be checked against the source in
   `C:\git\uol-dlip\digital-preservation` before it is written. When the old documentation and the
   code disagree, the code wins, and the discrepancy is recorded in `scratch/findings.md`
   (with a note on whether it looks like a docs error or a code bug).
2. **Preservation API first.** Most readers only ever have access to the Preservation API.
   Concepts are introduced in the Preservation API section; the Storage API section only
   describes where the Storage API differs.
3. **Digestible pages.** One topic per page, roughly 100–400 lines. Split rather than scroll.
4. **Samples, not just prose.** Important operations are accompanied by a Python sample in
   `preservation-docs-client/`, linked from the page with a `LinkCard` whose title starts with 💻.

## Site conventions

- Pages are `.mdx`. Frontmatter: `title`, and `sidebar: { label, order }` to control ordering.
- Directory name under `site/src/content/docs/` = sidebar group (configured in `astro.config.mjs`).
- **Internal links use the `../` prefix** for sibling pages, e.g. `[Deposits](../deposits)`,
  and `../../group/page` across groups. Starlight serves pages with a trailing slash, so a bare
  relative link resolves wrongly. Same-page anchors (`#section`) need no prefix.
- Components from `@astrojs/starlight/components`:
  - `Aside` (types `note`, `tip`, `caution`, `danger`) replaces GitHub `> [!NOTE]` alerts.
  - `LinkCard` for links to Python samples (💻 in the title) and to related pages.
  - `Card`/`CardGrid` on overview pages only.
  - `Steps` for numbered walk-throughs.
- Example hostnames: `https://preservation-api.example` (Preservation API),
  `https://storage-api.example` (Storage API), `https://preservation.example` (UI),
  `s3://working-bucket/deposits/<id>/` (deposit workspace). Never real Leeds hostnames.
- HTTP examples: a fenced block showing the request line, then a `json`/`jsonc` block for bodies.
- Property tables: `| Property | Description |`.
- Images go in `site/src/assets/` and are imported, or in `site/public/` for static files.

## Python sample conventions

- Samples live in `preservation-docs-client/p{NN}_{topic}/`, numbered by the sidebar order of
  the page they accompany.
- Every sample imports from `preservation.py` (HTTP helpers, auth) and `settings.py`
  (from `.env`). S3 uploads use `s3_helpers.py` (boto3).
- The code is deliberately simple: no async, no error handling, no retries. It exists to show
  the HTTP operations as clearly as possible.
- The samples are written for someone using a HOSTED instance of the platform, not a developer
  running it locally. `DISABLE_AUTH=true` exists only for the local case.
- Auth stance: the API expects a bearer JWT obtained by the standard OAuth2 client-credentials
  grant from whichever identity provider the platform instance is configured with. Today that
  provider is Microsoft Entra ID; document Entra as the *current concrete example* (token endpoint
  and scope forms), not as the design. The samples POST to a generic `TOKEN_ENDPOINT` (no MSAL).
  Every request also sends `X-Client-Identity`, which the API records as who did what.
- The LinkCard `href` is the GitHub URL:
  `https://github.com/digirati-co-uk/digital-preservation-docs/blob/main/preservation-docs-client/{dir}/{file}.py`
