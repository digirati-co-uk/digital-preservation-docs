# METS editability

This page defines **which METS files the platform may edit, and what editing does to them**. It is
the specification the editability decision is made against — for the platform's own METS, and for
METS written by other systems (EPrints, Archivematica, Goobi) that Leeds needs the platform to work
with.

It complements [The METS files we write](./02b-METS-Written-by-the-Platform.md) — the normative
profile of the platform's own output, which is also the shape an edited document ends up in — and
[What the METS parser can read](./02c-METS-Parsing.md), which is a much wider set than what can be
edited.

> [!NOTE]
> **Status, August 2026.** This page records the *agreed direction* (issue
> [#223](https://github.com/digirati-co-uk/digital-preservation/issues/223); plan in
> [`docs/issues/223/issue-223-editability-plan.md`](https://github.com/digirati-co-uk/digital-preservation/blob/main/docs/issues/223/issue-223-editability-plan.md)).
> The platform's *current* behaviour is simpler and stricter: a METS file is editable if and only
> if its `mets:agent` name is exactly the platform's own. The conformance-based rules below replace
> that gate once the #188 ID migration has bedded in and the corresponding platform changes land.

## Three words, strictly ordered

Editability conversations go wrong when one word does three jobs. These three are distinct, and
each implies the one before:

1. **Parseable** — `MetsParser` can read the document into the platform's model. The parser is
   deliberately forgiving; it exists to read METS from anywhere, including shapes not seen yet. We
   hope *everything* is parseable. Failure to parse is a diagnostic about the document, never a
   policy judgment about it.
2. **Navigable** — the document's physical structure resolves to a complete, unambiguous tree of
   deposit-relative paths (in implementation terms: the path cache builds with no diagnostics).
   Navigability is what the UI tree, diffing and read-modify need. A document can be perfectly
   parseable and not navigable — Goobi's presentation METS parses fine, but its file locations are
   IIIF URLs, not paths in the deposit.
3. **Editable** — the platform may mutate the document and save it. Requires navigability, plus the
   structural invariants the editing code relies on, **plus policy** — some documents that could
   mechanically be edited must not be (see the first principle below).

"Conformance" on this page always means conformance to a *named tier* below — never a loose
synonym for any of the three words above.

## Two principles

**Conformance is necessary but not sufficient.** A document with a living external editor is not
editable here even if it conforms, because two writers with different models silently corrupt each
other's work. This — not its shape — is the decisive reason Goobi METS is never editable: Goobi
actively re-edits its own documents. Any future source whose METS "looks fine" gets the same
question first: *is anything else still writing this document?*

**A resolved path must be deposit-relative.** Every editability tier requires that every file
location resolves to a relative path inside the deposit. This guard is what keeps a presentation
METS full of `https://…` locations from ever counting as navigable, and it travels with every
tolerance rule below — never one without the other.

## The classification

| Source | Parseable | Navigable | Editable |
|---|---|---|---|
| Platform-written ([02b profile](./02b-METS-Written-by-the-Platform.md)) | yes | yes | **yes** |
| EPrints-migrated | yes | yes, under the declared assumptions below | **yes, with declared assumptions** — the first save restructures to the 02b profile |
| Archivematica | yes | partially (needs case-insensitive `TYPE="physical"`; some directory divs lack ADMID) | **no** — read-only |
| Goobi | yes | no — file locations are absolute IIIF URLs, failing the deposit-relative guard | **never** — and would remain so regardless of shape, per the first principle |
| Anything else | hopefully | judged per document | only if it reaches an editable tier, judged from the document itself |

The `mets:agent` name plays no part in the decision. It remains in the document as provenance,
nothing more — which also closes the current rule's other weakness, that a hand-damaged document
*with* the right agent name counts as editable while being unsafe to edit.

## The EPrints tier: editable under declared assumptions

EPrints-migrated METS is flat: a root div and one div per file, no directory divs, every
`FLocat/@xlink:href` already a deposit-relative path under `objects/`. Measured against the real
corpus (a 410-file document: 410 paths resolved, zero diagnostics), it is fully navigable under
these reading rules — each a tolerance for something METS makes optional, none changing a byte on
disk:

1. **An untyped `structMap` is read as physical** when it is the only candidate. METS makes `TYPE`
   optional; absence is not contradiction.
2. **`TYPE` comparison is case-insensitive** on `structMap` and `div` alike.
3. **An untyped `div` carrying an `fptr` is read as an Item.**
4. **The `objects` container is implied.** No div for `objects/` exists, but every file path is
   under it; the root container is synthesised on read from the paths. Reading never writes it
   back.
5. **The file groups are mapped.** These documents carry fileGrps with USE values like
   `reference`, `original` or `DEFAULT` — EPrints writes *one group per file*, all
   `USE="reference"` — rather than the platform's single `USE="OBJECTS"`. All the groups the
   physical structMap references are treated together as the OBJECTS-equivalent, and consolidated
   into one `USE="OBJECTS"` group on save. What fails the tier is genuine ambiguity: referenced
   files sitting in groups with *different* USE values (which copy is the content?), or two
   referenced entries resolving to the same deposit-relative path.
6. **Every resolved path is deposit-relative** — the standing guard.

Because these documents have no directory divs, nothing in them needs `premis:originalName` on
read. The first directory div such a document ever acquires is the `objects` div materialised on
save, below.

### Quirks measured in the production corpus

The assumptions above were checked against recent production EPrints migrations (2025–2026
ingests, from single-file items to a 355-file item) and held in every document. The same check
surfaced two quirks the machinery must handle:

- **Every file's techMD carries a `premis:storage`/`contentLocation` holding a `file://` URL** —
  the file's path on the EPrints server it was migrated from. It is historical provenance, not a
  live location, and it is never rewritten; when the platform records a storage location of its
  own (on Archival Group export) it adds a separate `premis:storage` marked with its own
  `storageMedium`, alongside. The editing stack already reads storage assertions by
  `storageMedium`; the parser currently does not (it takes any single `contentLocation`, and
  fails on two), which must be corrected before third-party editing is enabled.
- **EPrints writes its record identifiers in the METS namespace, not MODS** —
  `recordInfo`/`recordIdentifier` elements carrying the EPrints id, the EMu number, and the
  `id.library.leeds.ac.uk` PID. The parser currently reads only `mods:recordIdentifier`, so these
  are invisible to the platform today. The judge, and eventually the parser, should read them;
  an edit that sets record info through the platform writes standard `mods:recordInfo` while the
  original EPrints elements are preserved untouched in place.
- **The referenced dmdSec claims MODS but is not MODS** — `mdWrap MDTYPE="MODS"` with no
  `mods:mods` record. Such a section is not editable as MODS and the platform never edits it;
  see the foreign-dmdSec rule in the save contract below.
- **`mdWrap` payloads are not wrapped in `mets:xmlData`** — EPrints puts `premis:object`
  directly inside `mdWrap`, which the METS schema does not allow (the content model is
  `binData`/`xmlData`). Harmless to the forgiving parser, but lethal to any schema-typed round
  trip, which would silently drop the payload — every checksum in the document. The save
  normalises the wrapper as a declared mutation; the payload is preserved verbatim.

## Editability covers the whole editable surface

"Editable" licenses everything the platform can do to a document — physical structure edits,
descriptive metadata (titles, access conditions, rights, record identifiers), **logical
structMaps** (whole-file pointers, time segments, image regions), and **file-to-file links** —
not just the physical tree the tiers are named for. Editability means the platform understands
the document and can change it; it cannot safely change linkage it cannot resolve. So both
editable tiers also require, for every document:

- every `fptr` and every `area` in **every** structMap — logical included — resolves through the
  fileSec;
- every `fptr` in the judged *physical* structMap carries a `FILEID` of its own — the platform's
  physical walk requires it; area-only pointers belong in logical structMaps, where the platform
  itself writes them;
- every file has exactly one `FLocat`, carrying an `xlink:href` — the platform's parser reads
  the single location of each file and cannot load zero, several, or one without an href;
- every href is already normalised — no empty or `.` segments — because the platform's path
  cache does not normalise paths, so `objects//a.jpg` is a real entry the platform can never
  reach;
- every directory div in the platform tier carries a `LABEL` — adding into a LABEL-less parent
  fails;
- both ends of every `structLink/smLink` resolve, whether they point at files (the platform's
  own arcrole style) or at divs (Goobi's logical-to-physical style);
- every logical structMap's root div has an ID — logical structure is edited *by address*
  (replaced, reordered and removed by root div ID), so an ID-less logical map is present but
  unchangeable, which is exactly what editable must not mean;
- SHA256 fixity per file **with an actual digest value**, in both tiers — every edit ends in an
  import job, and import jobs require it; an algorithm label with an empty digest is a record of
  having lost the checksum, not of having one.

When a document holds more than one physical-candidate structMap, **only the judged one is
judged**: an unchosen sibling map — preserved as parsed, never edited — can neither demote the
verdict nor satisfy a tier on the judged map's behalf.

A failure of any of these leaves the document navigable-read-only at best: its files can be
listed, but its structure cannot be safely mutated.

Deliberately *not* required: DMDID resolution. A dangling `DMDID` is by design in the platform's
own skeleton — dmdSecs are created lazily, references first — so it can never be a conformance
rule; what a *resolved* dmdSec must look like is covered by the foreign-dmdSec rule above.

## What saving does: restructure to the 02b profile

**On the first platform save, an EPrints-tier document is restructured to the
[02b profile](./02b-METS-Written-by-the-Platform.md).** The alternative — a document that stays in
its original shape until individual edits force platform conventions in piecemeal — would create a
third shape that is neither EPrints' nor the platform's, and that hybrid is the worst outcome for
every future reader. One save, one transition; the document is 02b thereafter.

What makes this acceptable, stated plainly because it is the part that matters to anyone whose
own tooling touches these documents:

- **The restructure rides along with a real edit.** Applying a rights statement or access condition
  was always going to create a new OCFL version, a published Activity Stream event, and a IIIF
  manifest rebuild. Nothing is mass-transformed: the reading tolerances above cover the whole
  corpus forever, and restructuring happens lazily, per document, on the first edit somebody
  actually wanted to make.
- **Existing IDs survive, all of them.** `eprint_10315_370441` is a legal `xs:ID`, and the
  platform's rule is that a legal ID is left alone whoever minted it (see
  [METS identifiers](./02d-METS-Identifiers.md) — IDs are opaque to code). Only elements the save
  *creates* get platform-minted IDs.
- **Provenance stays honest.** The original CREATOR agent stays; the platform is added as a
  modifying agent. The header keeps the document's history legible.

Concretely, the first save:

1. writes `TYPE="PHYSICAL"` onto the structMap and gives divs their types
   (`Directory`/`Item`);
2. **materialises the implied `objects` div**: a real Directory div with an `amdSec`/`techMD`
   carrying `premis:originalName` (`objects`), exactly as 02b specifies for any directory, and
   re-parents the file divs under it — where their paths always said they were;
3. consolidates the referenced fileGrps into the single `USE="OBJECTS"` group, moving the
   `mets:file` elements unchanged;
4. **wraps any bare `mdWrap` payload in the `mets:xmlData` element the schema requires** —
   EPrints puts `premis:object` directly inside `mdWrap`, which is schema-invalid and, left
   as-is, would be silently dropped by any schema-typed round trip. The wrapped content itself
   is preserved verbatim; only the missing wrapper is added;
5. appends the platform agent to `metsHdr`;
6. applies whatever the edit itself was, through the ordinary editing machinery;
7. **nothing else** — no ID renumbering, no reordering for its own sake, and sections the platform
   does not model are preserved as parsed, per the round-trip rules in 02b/02c.

**Descriptive metadata on a div whose dmdSec is foreign** deserves its own rule, because it is the
Leeds use case itself: the EPrints root div's `DMDID` points at a dmdSec that claims MODS but
holds no `mods:mods` record (and mostly wrong-namespace elements). **The platform never edits a
foreign dmdSec.** An edit that sets metadata on such a div creates a *new* platform dmdSec and
**appends** its ID to the div's `DMDID` — `DMDID` is IDREFS, so
`DMDID="DMD_eprint_10315 DMD_PHYS_ROOT"` is legal METS; the original section stays byte for byte,
and effective-metadata resolution reads both. (One prerequisite: the parser currently reads only
the *first-resolving* dmdSec of several — identifier-audit finding M10 — so fixing that joins
#236 and #237 as work the editing capability depends on.)

The mirror-image rule: a **MODS-editable dmdSec referenced from more than one div** makes the
document read-only, because editing metadata on one div would rewrite the shared section in
place and silently change the other div's metadata (identifier-audit finding P5). Sharing a
*foreign* dmdSec is fine — the platform never writes into those.

**If your code re-reads one of these documents after a platform save**: you will find an explicitly
typed physical structMap, an `objects` Directory div with PREMIS metadata, and a single OBJECTS
fileGrp — a *more* explicit document than was written originally, with every original ID intact.
Since EPrints-migrated documents are scripted, one-off migration outputs, external re-editing is
not expected; if it happens anyway, what it finds is legal METS stating outright what the original
left implied.

## The judge

The editability decision is implemented as a runnable check — one behaviour, two implementations
(.NET and Python), so that both the platform and external tooling can ask the same question and get
the same answer. Given a METS document it returns:

- a **verdict**: `editable` (02b tier) · `editable-with-normalisation` (EPrints tier — a save will
  restructure as above) · `navigable-read-only` (Archivematica tier) · `not-editable`;
- the **reasons** — every rule failed or satisfied-by-assumption, in actionable terms;
- for `editable-with-normalisation`, the **list of mutations a save would perform** on this
  document — a dry run of the contract above.

Structural rules that XML can answer (typing per tier, fileSec shape, header requirements,
ADMID/DMDID/FILEID referential integrity, SHA256 fixity presence) are expressed once as Schematron
and shared by both implementations; what Schematron cannot see (path normalisation and uniqueness,
the deposit-relative guard, implied-`objects` inference, fileGrp ambiguity) is native code on each
side, specified by this page.

## Current behaviour, for completeness

Until the changes described here land, the platform's rule is: **editable ⇔ the first `mets:agent`
name is exactly `University of Leeds Digital Library Infrastructure Project`** (see
[02c](./02c-METS-Parsing.md#header-information-name-agent-editability)). Everything else is
read-only — readable, diffable, preservable, never modified.

One measured detail worth knowing while that is true: the tolerances in the EPrints tier are not
yet in the *editing* stack. `MetsParser` already accepts `TYPE="physical"` case-insensitively and
untyped structMaps (which is why these documents are parseable today), but the path cache that
editing relies on requires the exact string `PHYSICAL` — so Archivematica and EPrints documents
are currently parseable but not navigable. That gap is precisely what the reading tolerances close.
