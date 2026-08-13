# What the METS parser can read

The platform's `MetsParser` (in the `DigitalPreservation.Mets` library) reads METS files from many sources — not just the files the platform writes itself. Deposits can arrive with METS produced by Archivematica, EPrints, Goobi, or by hand, and the parser extracts a common model from all of them:

- the **physical structure**: the tree of directories and files, with paths, names, digests, sizes and formats;
- **technical metadata** per file: PRONOM format, extents (duration, pixel dimensions), virus-scan results, Exif output;
- **descriptive metadata** per file, directory and logical division: access restrictions, rights statements, catalogue record identifiers, titles;
- the **logical structure**: trees of ranges pointing at whole files, time segments or image regions;
- **file-to-file relationships** (e.g. audio → transcript).

The parser is deliberately tolerant. It does not build a complete representation of the METS document; it hunts for the information above wherever a given profile puts it, and it accommodates considerable variation. When a new flavour of METS appears that it can't extract the necessary information from, the parser should be extended to understand that flavour. It uses plain `XDocument`/LINQ processing with no schema binding, precisely so that unpredictable third-party structure doesn't break it.

The counterpart page, [The METS files we write](./02b-METS-Written-by-the-Platform.md), specifies the platform's own METS output — which is of course also parseable, and is used as the round-trip format for editing.

## Locating the METS file

Given a deposit (or exported Archival Group) location, the parser finds the METS file as follows:

1. If the supplied URI ends in `.xml`, that file *is* the METS — the caller has told us so.
2. Otherwise, list the immediate children of the location: the first file named exactly `mets.xml` wins; failing that, the first `.xml` file whose name contains `mets` (case-insensitive) — this catches names like `EPrints.10315.METS.xml` or `METS.299eb16f-….xml`.
3. If nothing matches at the root, look inside a `data/` subdirectory the same way — a **BagIt layout**, where the bag's payload directory holds the METS and content.

All paths in the METS (`xlink:href`, IDs, `premis:originalName`) are then interpreted relative to the METS file's own directory.

The METS file does not usually describe itself; the parser adds an entry for the METS file to the parsed structure so that consumers see the complete file list.

## Header information: name, agent, editability

- The object's **name** is the first `mods:title` anywhere in the document, falling back to the first `mods:name`. (In EPrints METS the MODS elements are not wrapped in `<mods:mods>`; the parser searches the whole document, so this still works.)
- The **agent** is the name of the first `mets:agent`.
- The wrapper is flagged **editable** only when the agent is exactly `University of Leeds Digital Library Infrastructure Project`. Any other agent — `Archivematica`, `Goobi - 447dc - …`, or none — makes the METS read-only to the platform: we will read it, diff it, preserve it, but never modify it.

## Finding the physical structMap

There may be several `mets:structMap` elements, with or without `TYPE` attributes. The parser picks:

1. the first structMap with `TYPE="physical"` (case-insensitive), if there is one;
2. otherwise the first structMap that is not explicitly `TYPE="logical"` — EPrints structMaps have no TYPE at all, and this rule selects them.

A METS file with no usable physical structMap is rejected — this is the one hard requirement.

All of the following are parseable:

### Archivematica structMap and fileSec

```xml
<mets:structMap TYPE="physical" ID="structMap_1" LABEL="Archivematica default">
    <mets:div TYPE="Directory" LABEL="ARTCOOB9-299eb16f-1e62-4bf6-b259-c82146153711" DMDID="dmdSec_1">
        <mets:div TYPE="Directory" LABEL="objects" DMDID="dmdSec_2">
            <mets:div TYPE="Directory" LABEL="Edgware Community Hospital">
                <mets:div TYPE="Item" LABEL="03_05_01.tif">
                    <mets:fptr FILEID="file-23eacb1b-d9d3-4181-9601-c10dc8a23a48" />
                </mets:div>
                <mets:div TYPE="Item" LABEL="03_05_02.tif">
                    <mets:fptr FILEID="file-6158701f-4993-4016-82cc-ec5dbdc99e3e" />
                </mets:div>
                ...

<mets:fileSec>
    <mets:fileGrp USE="original">
        ...
        <mets:file ID="file-23eacb1b-d9d3-4181-9601-c10dc8a23a48" GROUPID="Group-23eacb1b-..." ADMID="amdSec_1">
            <mets:FLocat xlink:href="objects/Edgware_Community_Hospital/03_05_01.tif" LOCTYPE="OTHER" OTHERLOCTYPE="SYSTEM" />
        </mets:file>
        ...
```

### EPrints structMap and fileSec

```xml
<mets:structMap>
  <mets:div DMDID="DMD_eprint_10315" ADMID="AMD_eprint_10315">
    <mets:div>
      <mets:fptr FILEID="eprint_10315_370441"/>
    </mets:div>
    <mets:div>
      <mets:fptr FILEID="eprint_10315_370442"/>
    </mets:div>
    ...

<mets:fileSec>
  <mets:fileGrp USE="reference">
    <mets:file ID="eprint_10315_370441" SIZE="266036836" MIMETYPE="image/jpeg" ADMID="AMD_eprint_10315_370441">
      <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/372705s_001.jpg"/>
    </mets:file>
  </mets:fileGrp>
  ...
```

### Goobi structMap and fileSec

```xml
<mets:structMap TYPE="PHYSICAL">
    <mets:div DMDID="DMDPHYS_0000" ID="PHYS_0000" TYPE="physSequence">
        <mets:div ADMID="AMD_0001" ID="PHYS_0001" ORDER="1" ORDERLABEL=" - " TYPE="page">
            <mets:fptr FILEID="FILE_0001_OBJECTS" />
            <mets:fptr FILEID="FILE_0001_ALTO" />
        </mets:div>
        ...

<mets:fileSec>
    <mets:fileGrp USE="OBJECTS">
        <mets:file ID="FILE_0001_OBJECTS" MIMETYPE="image/jp2">
            <mets:FLocat LOCTYPE="URL" xlink:href="objects/b29356350_0001.jp2" />
        </mets:file>
        ...
    <mets:fileGrp USE="ALTO">
        <mets:file ID="FILE_0001_ALTO" MIMETYPE="application/xml">
            <mets:FLocat LOCTYPE="URL" xlink:href="alto/b29356350_0001.xml" />
        </mets:file>
        ...
```

### The platform's own structMap

See the [writer specification](./02b-METS-Written-by-the-Platform.md#physical-structmap) — path-derived IDs (`PHYS_objects/photo.tif`), `TYPE="Directory"`/`TYPE="Item"`, one fptr per Item div.

## Walking the physical structure

The parser walks the structMap divs recursively and merges what it finds with the paths in `mets:FLocat/@xlink:href`, which are the ground truth for where files actually live:

- A div with `TYPE="Directory"` (case-insensitive) is a directory; it **must have a `LABEL`**, which becomes the directory's display name. The directory's *path* comes from `premis:originalName` in the amdSec its `ADMID` points at, when there is one — that is the only way an *empty* directory can exist in the model.
- Divs of other types (`page`, `physSequence`, `Item`, untyped) are structural: their `mets:fptr` children yield files, and the div itself contributes nothing to the directory tree. In the Goobi example above, `physSequence` and `page` divs are skipped over; the directories `objects/` and `alto/` are inferred purely from the `xlink:href` paths.
- Every intermediate directory implied by a file path is created, so `objects/a/b/c.tif` yields `objects/`, `objects/a/`, `objects/a/b/` even if no div mentions them.
- A file's display name is the `LABEL` of the div containing its fptr (not `ORDERLABEL`), falling back to the last path segment.
- A structural root div with no `ADMID` but a `DMDID` (like our own `PHYS_ROOT`, or Goobi's `PHYS_0000` with `DMDPHYS_0000`) can't create a directory, but its descriptive metadata (access conditions, rights, record identifiers) is attached to the root of the physical structure, where the inheritance rules below can see it.
- `MIMETYPE` on the `mets:file` element, where present, becomes the file's content type. (Archivematica omits it; the content type is then derived from the PRONOM format.)

## Finding each file's technical metadata

The parser resolves the most appropriate PREMIS metadata for each file by following `ADMID`, which different producers put in different places:

- **On the `mets:file` element** — EPrints, Archivematica, and our own METS.
- **On the `mets:div`** — Goobi. A Goobi div can contain several fptrs (image + ALTO) but only one `ADMID`; the parser assumes the ADMID belongs to the *first* fptr in the div (true for Goobi at Wellcome — the ADMID describes the image, not the ALTO).

The `ADMID` may point at a `mets:techMD` directly, or at a `mets:amdSec` that contains one (Archivematica's style). Both are handled.

`ADMID` and `DMDID` are schema-typed **IDREFS** — a whitespace-separated list of references — and the parser handles both realities that creates:

- The **whole attribute value** is tried first. This is how METS the platform wrote before issue #188 keeps working: those IDs can themselves contain spaces (they embed file paths), so the reference attribute and the target's `ID` are the same raw string and match exactly.
- If the whole value resolves nothing and contains whitespace (space, tab or newline — all legal IDREFS separators), each **individual token** is tried in order. This is how a genuine multi-reference list (`ADMID="AMD_rights AMD_tech"`), common in Archivematica and Goobi METS, resolves. Because such a list routinely names sections a given caller has no use for — rights, source, provenance — a token that resolves to something unusable for the job in hand is **skipped**, and resolution walks on to the next.

The two tiers are deliberately asymmetric in that respect: the whole-value tier is an **identity** match, so if it resolves, that *is* the answer, usable or not. Walking on from it would mean resolving a *fragment* of a legacy ID against an unrelated section — reporting one file's rights, or one file's virus status, as another's. Callers therefore re-check what the identity tier hands back and report a precise diagnostic rather than quietly substituting a different section.

The techMD-then-amdSec fallback above applies to each candidate in turn. See [METS identifiers](./02d-METS-Identifiers.md) for the full story on why both forms exist.

## Reading the PREMIS object

Within the resolved techMD the parser looks for a `premis:object` — and although the *wrapping* differs between producers (`MDTYPE="PREMIS:OBJECT"` in ours, `MDTYPE="OTHER" MIMETYPE="text/xml"` in Goobi's and EPrints'; EPrints omits `mets:xmlData` entirely), the PREMIS content is handled uniformly:

- **Digest**: from `premis:fixity` where the algorithm normalises to sha256 — `SHA256`, `sha256` and `SHA-256` are all accepted. Digests using other algorithms are ignored (the platform requires SHA256 for import jobs).
- **Size**: `premis:size`, in bytes.
- **Format**: `premis:format` → `formatDesignation/formatName` (human-readable) and `formatRegistry/formatRegistryKey` where the registry is PRONOM (e.g. `fmt/353`). A file whose techMD has no usable format still gets format metadata with the PRONOM key `UNKNOWN`, so "identified as unknown" is distinguishable from "never looked at".
- **Original name**: `premis:originalName` — Archivematica values like `%transferDirectory%objects/...` are preserved as-is.
- **Storage location**: `premis:storage/premis:contentLocation`, parsed as a URI when present (this appears in METS the platform generates when exporting an Archival Group, recording the file's location in preservation storage).

Examples of all three third-party PREMIS variants:

### Archivematica PREMIS object

```xml
<mets:techMD ID="techMD_2">
    <mets:mdWrap MDTYPE="PREMIS:OBJECT">
        <mets:xmlData>
            <premis:object xmlns:premis="http://www.loc.gov/premis/v3" xsi:type="premis:file" version="3.0">
                <premis:objectIdentifier>
                    <premis:objectIdentifierType>UUID</premis:objectIdentifierType>
                    <premis:objectIdentifierValue>6158701f-4993-4016-82cc-ec5dbdc99e3e</premis:objectIdentifierValue>
                </premis:objectIdentifier>
                <premis:objectCharacteristics>
                    <premis:compositionLevel>0</premis:compositionLevel>
                    <premis:fixity>
                        <premis:messageDigestAlgorithm>sha256</premis:messageDigestAlgorithm>
                        <premis:messageDigest>8a45d8f39197f48f1196d0d7240096286e2b5fc8133bcf5e0d28eaabcc9dd4fa</premis:messageDigest>
                    </premis:fixity>
                    <premis:size>2388780</premis:size>
                    <premis:format>
                        <premis:formatDesignation>
                            <premis:formatName>Tagged Image File Format</premis:formatName>
                        </premis:formatDesignation>
                        <premis:formatRegistry>
                            <premis:formatRegistryName>PRONOM</premis:formatRegistryName>
                            <premis:formatRegistryKey>fmt/353</premis:formatRegistryKey>
                        </premis:formatRegistry>
                    </premis:format>
                </premis:objectCharacteristics>
                <premis:originalName>%transferDirectory%objects/Edgware_Community_Hospital/03_05_02.tif</premis:originalName>
            </premis:object>
        </mets:xmlData>
    </mets:mdWrap>
</mets:techMD>
```

### EPrints PREMIS object

```xml
<mets:techMD ID="AMD_eprint_10315_370441">
  <mets:mdWrap MDTYPE="OTHER" MIMETYPE="text/xml">
    <premis:object xsi:type="premis:file">
      <premis:objectIdentifier>
        <premis:objectIdentifierType>local</premis:objectIdentifierType>
        <premis:objectIdentifierValue>372705s_001.jpg</premis:objectIdentifierValue>
      </premis:objectIdentifier>
      <premis:objectCharacteristics>
        <premis:fixity>
          <premis:messageDigestAlgorithm>sha256</premis:messageDigestAlgorithm>
          <premis:messageDigest>4675c73e6fd66d2ea9a684ec79e4e6559bb4d44a35e8234794b0691472b0385d</premis:messageDigest>
        </premis:fixity>
        <premis:size>876464</premis:size>
        <premis:format>
          <premis:formatDesignation>
            <premis:formatName>JPEG File Interchange Format</premis:formatName>
          </premis:formatDesignation>
          <premis:formatRegistry>
            <premis:formatRegistryName>PRONOM</premis:formatRegistryName>
            <premis:formatRegistryKey>fmt/43</premis:formatRegistryKey>
          </premis:formatRegistry>
        </premis:format>
      </premis:objectCharacteristics>
    </premis:object>
  </mets:mdWrap>
</mets:techMD>
```

(Note: no `mets:xmlData` wrapper — the parser doesn't care.)

### Goobi PREMIS object

```xml
<mets:techMD ID="AMD_0001">
    <mets:mdWrap MDTYPE="OTHER" MIMETYPE="text/xml">
        <mets:xmlData>
            <premis:object version="3.0" xsi:type="premis:file">
                <premis:objectIdentifier>
                    <premis:objectIdentifierType>local</premis:objectIdentifierType>
                    <premis:objectIdentifierValue>b33061592_0001.jp2</premis:objectIdentifierValue>
                </premis:objectIdentifier>
                <premis:significantProperties>
                    <premis:significantPropertiesType>ImageHeight</premis:significantPropertiesType>
                    <premis:significantPropertiesValue>5860</premis:significantPropertiesValue>
                </premis:significantProperties>
                <premis:significantProperties>
                    <premis:significantPropertiesType>ImageWidth</premis:significantPropertiesType>
                    <premis:significantPropertiesValue>8148</premis:significantPropertiesValue>
                </premis:significantProperties>
                <premis:objectCharacteristics>
                    <premis:fixity>
                        <premis:messageDigestAlgorithm>SHA-256</premis:messageDigestAlgorithm>
                        <premis:messageDigest>dbb14f0374dae9b617e20da9400e9d7dbb0e1a514ac9bd124b35ac940f54e2b0</premis:messageDigest>
                    </premis:fixity>
                    <premis:size>17898927</premis:size>
                    <premis:format>
                        <premis:formatDesignation>
                            <premis:formatName>JP2 (JPEG 2000 part 1)</premis:formatName>
                        </premis:formatDesignation>
                        <premis:formatRegistry>
                            <premis:formatRegistryName>PRONOM</premis:formatRegistryName>
                            <premis:formatRegistryKey>x-fmt/392</premis:formatRegistryKey>
                        </premis:formatRegistry>
                    </premis:format>
                </premis:objectCharacteristics>
            </premis:object>
        </mets:xmlData>
    </mets:mdWrap>
</mets:techMD>
```

### Extents from significant properties

`premis:significantProperties` are read into extent metadata:

- `ImageWidth` / `ImageHeight` → pixel dimensions (integers);
- `Duration` → seconds. Both plain decimal (`2700`) and time-code (`00:45:00`, `00:35:09.5`) forms are accepted.

### Virus-scan events

Scan events **accumulate** rather than being replaced (see the [writer page](./02b-METS-Written-by-the-Platform.md#provenance-events-accumulate)), so an amdSec may hold several ClamAV events plus provenance events from other sources. What the parser wants is the file's *current* status, which is the **latest** ClamAV event present — not the first, and not the only one.

The event is found **structurally**: within the same `mets:amdSec` as the file's resolved techMD, the last `mets:digiprovMD` whose ID starts with `digiprovMD_ClamAV_` (case-insensitive) is the scan record. Provenance events the parser does not recognise are ignored, never treated as an error.

Only when nothing is found structurally does it fall back to looking the ID up by naming convention. That path matters more than it looks: it runs whenever the structural route cannot, which includes an ADMID resolving to a techMD carrying no `premis:object` (a MIX or FITS-only section, for instance). The fallback **constructs** the candidate IDs from the file's own resolved identifier — the plain `digiprovMD_ClamAV_{admId}` and the numbered `digiprovMD_ClamAV_{n}_{admId}` forms — and takes the highest occurrence found, so a rescanned file is never reported with its first scan's result. Matching is exact (case-insensitive) per candidate; containment matching was removed because it cross-talked between files whose IDs are prefixes of one another (`ADM_a` is contained in `ADM_a2`).

The `premis:event` within yields: outcome (`Pass`/`Fail` — outcome `fail` means a virus was found), the virus name from `eventOutcomeDetailNote`, the scanner/definitions from `eventDetail`, and the scan timestamp. See the [writer page](./02b-METS-Written-by-the-Platform.md#virus-scanning-digiprovmd--premis-event) for a full example.

### Exif blobs

An `<ExifMetadata>` element anywhere in the file's amdSec (the platform writes it inside `premis:objectCharacteristicsExtension`) is read back as a list of tag name/value pairs.

## Descriptive metadata from dmdSecs

Descriptive metadata is always resolved from a **div's** `DMDID` — files themselves are never assumed to carry a `DMDID`. From the MODS inside the dmdSec the parser reads:

- **Access restrictions**: every `mods:accessCondition` with `type="restriction on access"` — and also `type="status"`, which is where Goobi puts its access condition (`<mods:accessCondition type="status">Open with advisory</mods:accessCondition>`).
- **Rights statement**: `mods:accessCondition` with `type="use and reproduction"`, parsed as a URI. If the element is *present but not a valid URI* (e.g. the sentinel `null`), the parser records that rights were explicitly addressed — which suppresses inheritance (below) — while leaving the rights value empty.
- **Record identifiers**: every `mods:recordIdentifier`, with its `source` attribute.
- For logical divs, the **title**: `mods:title`, falling back to the div's `LABEL`.

## Logical structure

Every `mets:structMap TYPE="logical"` (case-insensitive) is parsed into a tree of logical ranges: ID, TYPE, name (DMD title or LABEL), descriptive metadata as above, child ranges, and file pointers. Two quite different linkage styles connect logical divs to content, and both are supported.

### Style 1: direct fptr (the platform's own style)

Logical divs contain `mets:fptr` elements pointing at files — either whole files, or parts of files via `mets:area`:

```xml
<mets:div ID="LOG_0002" LABEL="AITCHISON, BERTRAM STEWART" TYPE="Item" DMDID="DMD_LOG_0002">
  <mets:fptr>
    <mets:area FILEID="FILE_objects/tape1side1.wav" BETYPE="TIME" BEGIN="00:36:40" END="00:45:00"/>
  </mets:fptr>
  <mets:fptr>
    <mets:area FILEID="FILE_objects/tape1side2.wav" BETYPE="TIME" BEGIN="00:00:09.2" END="00:20:09"/>
  </mets:fptr>
</mets:div>
```

Area handling:

- `BETYPE="TIME"` with `BEGIN`/`END` time codes (`HH:MM:SS` or `HH:MM:SS.sss`) → begin/end in seconds. A malformed time code is logged and skipped; the file pointer survives without timing.
- `SHAPE="RECT"` with `COORDS="x1,y1,x2,y2"` → an image region.
- Both on one area → a spatio-temporal pointer (region of a video for a time window).
- Anything else (`BETYPE="BYTE"`, `SHAPE="CIRCLE"`/`POLY`, …) is not interpreted, but **all its attributes are preserved** so that editing the METS never destroys them — they are written back verbatim.
- The `FILEID` may sit on the `mets:area` or on the `mets:fptr`; either way it is resolved through the fileSec to the file's path.

### Style 2: structLink smLinks (Goobi's style)

Goobi logical divs carry no fptrs. Instead, `mets:structLink` maps logical div IDs to *physical* div IDs:

```xml
<mets:structMap TYPE="LOGICAL">
    <mets:div DMDID="DMDLOG_0000" ID="LOG_0000" LABEL="Woman on sofa..." TYPE="Archive">
        <mets:div DMDID="DMDLOG_0001" ID="LOG_0001" TYPE="Back" />
    </mets:div>
</mets:structMap>
<mets:structMap TYPE="PHYSICAL">
    <mets:div DMDID="DMDPHYS_0000" ID="PHYS_0000" TYPE="physSequence">
        <mets:div ID="PHYS_0001" ORDER="1" TYPE="page" ADMID="AMD_0001">
            <mets:fptr FILEID="FILE_0001_OBJECTS" />
        </mets:div>
        <mets:div ID="PHYS_0002" ORDER="2" TYPE="page" ADMID="AMD_0002">
            <mets:fptr FILEID="FILE_0002_OBJECTS" />
        </mets:div>
    </mets:div>
</mets:structMap>
<mets:structLink>
    <mets:smLink xlink:from="LOG_0000" xlink:to="PHYS_0001" />
    <mets:smLink xlink:from="LOG_0000" xlink:to="PHYS_0002" />
    <mets:smLink xlink:from="LOG_0001" xlink:to="PHYS_0002" />
</mets:structLink>
```

Multiple logical divs commonly claim the same physical page (in the example, both the whole item `LOG_0000` and its child `LOG_0001` claim `PHYS_0002`). The parser applies a **deepest-only rule**: each physical div's files are assigned to the *most specific* (deepest) logical range that links to it, so the resulting range tree is non-overlapping and can be used directly to build IIIF ranges. Files in fileGrp `USE="ALTO"` are associated with the range for metadata-inheritance purposes but are not added as the range's paintable content.

## File-to-file links

Two mechanisms yield "this file supplements that file" relationships:

**Explicit arcrole smLinks** — `mets:smLink` elements whose from/to are *file* IDs and which carry an `xlink:arcrole` URI:

```xml
<mets:structLink>
  <mets:smLink xlink:from="FILE_objects/amber-rudd.m4a" xlink:to="FILE_objects/amber-rudd.docx"
               xlink:arcrole="http://iiif.io/api/presentation/3#transcript" />
</mets:structLink>
```

(The presence or absence of `arcrole` is what distinguishes these from Goobi's logical→physical smLinks.)

**Inference from Goobi page divs** — when a physical div contains fptrs to both a `USE="OBJECTS"` file and a `USE="ALTO"` file, the ALTO file is inferred to be a **transcript** of the image:

```xml
<mets:div ADMID="AMD_0001" ID="PHYS_0001" ORDER="1" TYPE="page">
    <mets:fptr FILEID="FILE_0001_OBJECTS" />   <!-- objects/b29356350_0001.jp2 -->
    <mets:fptr FILEID="FILE_0001_ALTO" />      <!-- alto/b29356350_0001.xml → transcript link inferred -->
</mets:div>
```

## Effective metadata inheritance

Raw values only tell you what a div explicitly asserts. Consumers (validation, the iiif-builder) need to know what applies to each file *after inheritance*, so the parser computes **effective** access restrictions, rights statement and record info for every file, directory and logical range. The rules:

**Access restrictions and rights (physical files and directories):**

1. Use the resource's own explicit value if present.
2. Otherwise inherit from the nearest physical ancestor directory that has one. Physical always takes precedence — logical structure cannot *override* physical access/rights.
3. If the physical tree is silent, fall back to the file's logical assignment: the range that references it as a whole-file fptr (when exactly one does), or its deepest smLink-associated range. This handles METS — like Goobi's — where access conditions live entirely in logical dmdSecs.
4. If nothing yields a value, effective access is empty and rights is null. (Such files are candidates for a validation warning.)

**Rights suppression:** an *explicit but empty* `use and reproduction` element (present, but not a valid URI) is a deliberate "no rights statement" assertion. It stops inheritance dead: the file's — or directory's, including everything below it — effective rights is null, not the parent's value.

**Record info (physical files):**

1. Own explicit value if present.
2. Otherwise, if the file is referenced as a **whole-file** fptr in exactly one logical range, inherit that range's effective record info. (A file referenced only via `mets:area` — a tape carrying several interviews — belongs to no single range, so it cannot inherit from any; a file referenced by multiple ranges likewise.)
3. Otherwise, the range associated via smLink (this is how Goobi ALTO files pick up the record identifier of the section they belong to).
4. Otherwise walk up the physical directory tree.

**Logical ranges:** a range's effective access/rights is its own value, else inherited from the *root* descriptive metadata (`DMD_PHYS_ROOT` or the structural root div) — intermediate physical directories like `objects/` do not propagate to logical ranges. Effective record info is its own value, else its parent range's.

A worked example, from the "Women of Westminster" METS on the [writer page](./02b-METS-Written-by-the-Platform.md#a-complete-example): `objects/` carries access `Level1`, rights `InC`, record `MS 2249`; the logical range "Amber Rudd" carries record `MS 2249/1`; the file `angela-eagle.m4a` carries access `Closed` and the `null` rights sentinel.

| File | Effective access | Effective rights | Effective record |
|---|---|---|---|
| `amber-rudd.m4a` | `Level1` (from `objects/`) | `InC` (from `objects/`) | `MS 2249/1` (whole-file fptr in the "Amber Rudd" range) |
| `angela-eagle.m4a` | `Closed` (own) | *none* (own, suppressed) | `MS 2249` (not in any range → from `objects/`) |
| `tape1side1.wav` (Liddle tapes) | inherited from `objects/` | inherited from `objects/` | from `objects/` — referenced only as time-coded areas, so no range inheritance |

## What the parser does not do

- It does not validate against the METS schema, and it ignores sections it has no use for (Goobi's `dv:rights`/`dv:links`, Archivematica's `objectCharacteristicsExtension` tool dumps, `premis:event` histories other than virus checks, rightsMD, sourceMD…). Unknown material is not an error; it is simply not extracted — and since the platform never edits third-party METS, it is never lost either.
- It requires SHA256 fixity to make a file usable in an import job; other algorithms are ignored rather than converted.
- It does not follow `mets:mdRef` to external metadata files.
- Only `RECT` areas are modelled; `CIRCLE`/`POLY` (and non-TIME `BETYPE`s) are preserved for round-trip but not interpreted.
