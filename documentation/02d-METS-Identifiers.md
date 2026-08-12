# METS identifiers — how our IDs work

Every element in a METS file the platform writes carries an `ID` attribute, and the
structural elements cross-reference each other by those IDs. This page explains, in plain
terms, how those IDs are made, what you can and cannot rely on, and what is changing.

It complements [METS written by the platform](./02b-METS-Written-by-the-Platform.md) (the
full document shape) and [METS parsing](./02c-METS-Parsing.md) (how third-party METS is
read).

## The scheme: a prefix plus the path

An ID is a fixed prefix telling you what *kind* of thing it identifies, followed by the
resource's path within the deposit:

| Prefix | Identifies | Example |
|---|---|---|
| `PHYS_` | a div in the physical structMap | `PHYS_objects/photo.tif` |
| `FILE_` | a file in the fileSec | `FILE_objects/photo.tif` |
| `ADM_` | an amdSec (administrative metadata) | `ADM_objects/photo.tif` |
| `TECH_` | the techMD inside that amdSec | `TECH_objects/photo.tif` |
| `DMD_` | a dmdSec (descriptive metadata) | `DMD_objects/photo.tif` |
| `digiprovMD_ClamAV_` | a virus-scan event record | `digiprovMD_ClamAV_ADM_objects/photo.tif` |

The point of this scheme is **human readability**: open the XML and every element tells you
what it is and what it belongs to.

## The catch: these are not valid XML IDs

The METS schema types `ID` attributes as `xs:ID`, which must be an *NCName* — and an NCName
may not contain `/`, spaces, and various other characters that file paths contain freely.
So `PHYS_objects/my file.pdf` is doubly invalid (a slash *and* a space), and a validating
parser will reject the document. This is
[issue #188](https://github.com/digirati-co-uk/digital-preservation/issues/188).

A space in an ID causes a second, subtler problem. Reference attributes like `ADMID` and
`DMDID` are typed *IDREFS* — a **whitespace-separated list** of IDs. An ID that contains a
space is therefore indistinguishable, to standard tooling, from two references. Typed
deserialisers split it in half.

## The fix, and the promise underneath it

The fix is sequenced so that **every METS file already written stays readable and editable,
unchanged, indefinitely**. That promise shapes everything:

1. **Step 1 (landed): IDs stopped being load-bearing.** The platform no longer navigates by
   ID text. It builds a *path cache* from the metadata that genuinely records where things
   are — `premis:originalName` for directories, `FLocat/@xlink:href` for files — and treats
   the ID as an opaque label. Reference attributes are resolved tolerantly on both the
   writing and parsing stacks: the whole attribute value is tried first (which is exactly
   how a legacy space-containing ID matches), then each whitespace-separated token (which is
   how a genuine multi-reference list resolves).
2. **Step 2 (pending): new IDs become schema-valid.** Newly written entries will encode the
   path part with `XmlConvert.EncodeLocalName` — `/` becomes `_x002F_`, a space becomes
   `_x0020_` — so `PHYS_objects/my file.pdf` is minted as
   `PHYS_objects_x002F_my_x0020_file.pdf`. Existing entries keep the IDs they were born
   with, so a document edited after step 2 can legitimately contain **both forms side by
   side**. Because of step 1, nothing cares.
3. **Step 3 (deferred): bulk migration.** Only if and when every legacy document is
   deliberately rewritten do the old forms disappear.

## The rules, if you consume or produce this METS

- **Treat IDs as opaque.** Never parse a path *out of* an ID. The path lives in
  `FLocat/@xlink:href` (files) and `premis:originalName` (directories) — those are the
  ground truth, in both ID eras.
- **Resolve references by the raw string.** To follow an `ADMID`/`DMDID`/`FILEID`/smLink
  reference, match the attribute value against `ID` attributes exactly. If the whole value
  matches nothing and contains whitespace, try each token. (This is what the platform's own
  reader does.)
- **Copy IDs verbatim when writing references.** A reference must be the target element's
  actual `ID`, character for character — never reconstructed from a path or a naming
  convention. This is also the rule the platform's own step 2 work follows internally.
- **Don't assume uniqueness of shape.** Legacy IDs contain slashes and spaces; new ones
  contain `_x002F_`/`_x0020_` escapes; third-party METS (Goobi, Archivematica, EPrints)
  follows entirely different conventions (`AMD_0001`, `file-{uuid}`, …). All are just
  strings.

## Status

As of August 2026: step 1 and the IDREFS resolution work are implemented
(digital-preservation PRs #211 and #213); step 2 is planned; step 3 is deferred. This page
describes behaviour as of #213.
