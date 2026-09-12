# Findings F: METS section (mets/ pages)

Discrepancies found while porting `documentation/02a`–`02e` into `site/src/content/docs/mets/`,
checked against `digital-preservation` `main` (f8ccd55) on 2026-09-11. Each entry says what the old
page claimed, what the code does, and how the site page was phrased.

## Open

### F1. Virus-scan events are recognised by `premis:eventType`, not by ID prefix (02c stale)
- 02c "Virus-scan events" says the parser takes "the last `mets:digiprovMD` whose ID starts with
  `digiprovMD_ClamAV_`".
- Code: `MetsParser.IsVirusCheckEvent` matches `premis:eventType == "virus check"`
  (`Constants.VirusCheckEventType`, case-insensitive); the `digiprovMD_ClamAV_` prefix is only used
  by the conventional-key *fallback* (`LatestByConventionalKey`). A digiprovMD wrapping several
  events yields the last one typed `virus check`.
- Site: `mets-we-read.mdx` and `mets-we-write.mdx` describe the eventType rule. Docs error (stale
  after the #221/#188 follow-ups); no code bug.

### F2. The editability judge (PR #238) is still open
- 02e reads as if the judge exists ("is implemented as a runnable check").
- Code: PR #238 (`feat/223-editability-judge`) is OPEN as of 2026-09-11; there is no
  `DigitalPreservation.Mets.Conformance` project on `main`. The shipped rule remains
  `mets.Editable = mets.Agent == Constants.MetsCreatorAgent` (`MetsParser.cs` lines 254/270).
- Site: `editability.mdx` says the judge "is designed as" a runnable check and states explicitly
  that it is not yet part of the platform, linking PR #238. **Revisit when #238 merges.**

### F3. 02d "Status" is stale on the migration campaigns
- 02d says the campaigns "have been surveyed and sized but not yet run".
- The development campaign has since run (early September 2026); production is pending platform
  release. This is operational state, not code, so the site page avoids dating it: "operational runs
  of the tool rather than code changes; until they have completed in every environment…".
  Update the wording once the production campaign completes (mixed-form rules then stop being
  load-bearing, and the two legacy fallbacks named on the identifiers page become removable).

### F4. Feature flag names not in the old docs
- 02b/02d refer to "the migration feature flag" without naming it.
- Code: `FeatureFlags:NormaliseMetsIdsOnWrite` (`MetsManagerOptions`, read in
  `MetsManager.NormaliseOnWrite`) controls normalise-on-write; the UI action is separately gated by
  `FeatureFlags:ShowNormaliseMetsIds` (`Deposit.cshtml.cs`). Site names the first; the second is a
  UI concern for the `ui/` section.

### F5. Normaliser refuses documents with duplicate IDs (not in 02d)
- Code: `MetsIdNormaliser.PlanRewrites` refuses (returns a report with `DuplicateIds`) before
  touching anything when two elements share an ID; `MetsManager.NormaliseIds` surfaces this as a
  failure. Added to `identifiers.mdx` step 3. Docs omission, not a bug.

### F6. Code location: `DigitalPreservation.Mets`, not `Storage.Repository.Common/Mets`
- The porting brief (and the code repo's own `CLAUDE.md`) place `MetsManager`/`MetsParser` under
  `Storage.Repository.Common/Mets/`. On `main` they live in
  `src/DigitalPreservation/DigitalPreservation.Mets/` (with `MetsIds.cs`, `MetsIdNormaliser.cs`,
  `MetsCache.cs`, `PremisEventManager.cs`, etc.). 02b/02c already say `DigitalPreservation.Mets`;
  the site links to that path. The code repo's `CLAUDE.md` is what is stale.

## Verified (no discrepancy)

- ID prefixes `PHYS_`/`FILE_`/`ADM_`/`TECH_`/`DMD_`, `DMD_PHYS_ROOT`, `PHYS_ROOT`/`__ROOT`,
  `digiprovMD_ClamAV_` and the between-prefix-and-identifier occurrence number
  (`Constants.NumberedVirusProvEventId`), `XmlConvert.EncodeLocalName` encoding via `ToMetsId()`,
  `MetsIds.Normalise` leaving legal IDs untouched — all as documented.
- Agent name `University of Leeds Digital Library Infrastructure Project`; root title fallback
  `[Untitled]`; children sorted by lower-cased label (`MetsManager` line 461).
- Caller-supplied logical range IDs are validated with `XmlConvert.VerifyNCName` and rejected
  (`MetsManager.SetStructMap`), not encoded.
- Parser structMap selection: `TYPE="physical"` case-insensitive first, else first not-`logical`.
  Editing stack (`MetsCache.Build`, `MetsManager` line 781) requires the exact string `PHYSICAL`
  (`Constants.Physical`), so the "parseable but not navigable" gap in 02c/02e is real.
- Parser reads one `premis:contentLocation` via `SingleOrDefault` (throws on two), matching 02e's
  EPrints `file://` quirk note. Goobi access condition read from `type="status"`; record identifiers
  read only from `mods:recordIdentifier`; name = first `mods:title` else `mods:name`.
- `Bitrate` significant property comes from the Exif `AvgBitrate` tag; video dimensions prefer
  `ImageSize`, then `SourceImageWidth/Height`, then `ImageWidth/Height` (`PremisManagerExif`).
- Link targets exist on `main`: `docs/issues/223/issue-223-editability-plan.md`,
  `src/mets-id-migration/`, `DigitalPreservation.Mets/{MetsIds,MetsManager,MetsParser}.cs`.

## Cross-links that depend on other sections

`mets/` pages link to `../../preservation-api/deposits#templates`, `../../preservation-api/editing-mets`
and `../../preservation-api/vocabularies`. Only `preservation-api/overview.mdx` exists at the time of
writing; the build will report broken links until those pages land.
