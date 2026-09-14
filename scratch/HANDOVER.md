# Handover: the documentation site

Updated 2026-09-12. Read this, then `../CLAUDE.md` (conventions) and `site-plan.md` (page slugs).

## Where it got to

**Content complete.** 46 pages on branch `docs-site`, building clean. Every section of
`site-plan.md` is written: introduction (quickstart, overview, concepts, components),
preservation-api (17 pages), workflows (9), mets (6), ui (5), storage-api (4).

- **Verified twice.** Written against the code, then re-checked by independent agents. 17 errors
  in the first 23 pages; 20 errors and 4 broken sequences in the remaining 22. The second pass is
  not optional - the base rate was high.
- **All 30 samples run** against the dev instance (p01-p15, w02-w08). Running them found four
  programs sending `If-Match: None` and a helper with a syntax error that had never executed.
- **2,552 internal links and anchors resolve.** Checked by crawling `dist/`, not the sources.
- **Eight screenshots** in `site/src/assets/ui/`, emails and hostnames sanitised before capture.
- **Ten issues filed** on the code repo: #258-#260, #262-#268. See `findings.md`.

## What is left

1. **Merge `docs-site`.** It sits on `mets-profiles`, which is still unmerged - rebase when that
   lands. Pages source must be "GitHub Actions" in repo settings; the old `gh-pages` branch is a
   Jekyll site of sequence diagrams.
2. **The site describes the `feature/multiple-deposit-buckets` branch, not `main`** - `/whoami`,
   `KnownClients`, `depositBucket` routing, the pipeline's default-bucket refusal, the import-job
   suppression gate. Tom accepted this ("it's near release"), but check before publishing.
3. **No link checker is installed.** The sweep was a one-off script; consider
   `starlight-links-validator` so this does not rot.
4. **Fold `sequence-diagrams/` in** and retire the `gh-pages` Jekyll workflow.
5. **Decisions waiting on Tom**, in `findings.md` under "Needs a decision, not a patch": the Binary
   `content` URI, whether unenforced import-job requirements should be enforced, and the Storage API
   example shipping `DisableAuth: "true"`.

## How to work here

- **Keep Tom's prose.** Where the code still agrees with the original, keep his sentences; correct
  only what is wrong; write new text in the same voice. He asked for this explicitly and more than
  once.
- **The code wins over the old documentation**, and every discrepancy goes in `findings-*.md`.
  `documentation/*.md` now carries a superseded banner on every ported file; 02c, 02d and 02e carry
  a specific warning because they are wrong in ways that matter.
- **Run the samples.** See `preservation-docs-client/README.md`. The dev API is behind a private
  load balancer, so it needs the VPN; the UI answering proves nothing.
- **Verify short snippets hardest.** Three of the four broken sequences were in `recipes.mdx`,
  written from memory, including a route that has never existed.
- Two or three writing agents at a time is fine; eight is not.

## Where documentation lives now

- **This repo** - the site and the samples, for people *using* the platform.
- **Code repo `docs/internals/`** - overview, pipeline-api, deployment: building and running it.
- **uol-dlip/preservation-ops** - the authority for infrastructure. Do not restate it anywhere else.
- **iiif-builder is deliberately undocumented**: Leeds run their own fork.
