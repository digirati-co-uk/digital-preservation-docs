# The METS files we write

This page is a specification — a profile, though we don't claim formal METS Profile status — of the METS files that the platform itself creates and maintains. It describes what the `MetsManager` (in the `DigitalPreservation.Mets` library) writes when a Deposit has a *managed* METS file: one created from a Deposit template (`RootLevel` or `BagIt`) rather than supplied by a third party.

For the METS files we can *read* — which is a much wider set, including Archivematica, EPrints and Goobi output — see [What the METS parser can read](./02c-METS-Parsing.md).

The design principle throughout: **the METS file is the canonical record of everything we know about the object** — its files, their fixity and formats, tool output (format identification, virus scanning, Exif extraction), descriptive metadata, access conditions, and logical structure for presentation. The entire preservation state must be recoverable from the OCFL object alone, and the METS file inside it carries everything that isn't the bitstreams themselves.

## When the platform writes METS

- Creating a Deposit from a template writes a skeleton `mets.xml` at the deposit root (or at `data/mets.xml` for the `BagIt` template).
- Adding a file or folder to the deposit (via the Preservation API or UI) adds corresponding entries.
- Deleting a file or folder removes its entries.
- Running the pipeline (Brunnhilde/Siegfried, ClamAV, Exif tools) patches technical metadata into the entries for each file.
- Editing names, access conditions, rights, catalogue identifiers or logical structure updates the relevant sections.

A METS file is only treated as editable when its `mets:agent` name is exactly ours (see next section). Third-party METS is never modified.

Concurrent edits are guarded by the S3 ETag of the METS file: every read-modify-write cycle passes the ETag back, and a mismatch fails the operation rather than clobbering another writer's change.

## Document skeleton

A brand-new managed METS file, before any files have been added:

```xml
<mets:mets xmlns:mets="http://www.loc.gov/METS/"
           xmlns:mods="http://www.loc.gov/mods/v3"
           xmlns:premis="http://www.loc.gov/premis/v3"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <mets:metsHdr CREATEDATE="2026-06-15T15:48:23.1549777+01:00">
    <mets:agent ROLE="CREATOR" TYPE="OTHER" OTHERTYPE="SOFTWARE">
      <mets:name>University of Leeds Digital Library Infrastructure Project</mets:name>
    </mets:agent>
  </mets:metsHdr>

  <mets:dmdSec ID="DMD_PHYS_ROOT">
    <mets:mdWrap MDTYPE="MODS">
      <mets:xmlData>
        <mods:mods>
          <mods:titleInfo>
            <mods:title>My New Deposit</mods:title>
          </mods:titleInfo>
        </mods:mods>
      </mets:xmlData>
    </mets:mdWrap>
  </mets:dmdSec>

  <mets:amdSec ID="ADM_objects">
    <mets:techMD ID="TECH_objects">
      <mets:mdWrap MDTYPE="PREMIS:OBJECT">
        <mets:xmlData>
          <premis:object xsi:type="premis:file">
            <premis:objectCharacteristics />
            <premis:originalName>objects</premis:originalName>
          </premis:object>
        </mets:xmlData>
      </mets:mdWrap>
    </mets:techMD>
  </mets:amdSec>
  <mets:amdSec ID="ADM_metadata"><!-- same shape, originalName = metadata --></mets:amdSec>
  <mets:amdSec ID="ADM_metadata/ad-hoc"><!-- same shape, originalName = metadata/ad-hoc --></mets:amdSec>

  <mets:fileSec>
    <mets:fileGrp USE="OBJECTS" />
  </mets:fileSec>

  <mets:structMap TYPE="PHYSICAL">
    <mets:div ID="PHYS_ROOT" LABEL="__ROOT" DMDID="DMD_PHYS_ROOT" TYPE="Directory">
      <mets:div ID="PHYS_metadata" LABEL="metadata" DMDID="DMD_metadata" ADMID="ADM_metadata" TYPE="Directory">
        <mets:div ID="PHYS_metadata/ad-hoc" LABEL="ad-hoc" DMDID="DMD_metadata/ad-hoc"
                  ADMID="ADM_metadata/ad-hoc" TYPE="Directory" />
      </mets:div>
      <mets:div ID="PHYS_objects" LABEL="objects" DMDID="DMD_objects" ADMID="ADM_objects" TYPE="Directory" />
    </mets:div>
  </mets:structMap>
</mets:mets>
```

Things to notice, each expanded on below:

- The **agent name** identifies us as creator; this exact string is what makes a METS file *editable* by the platform.
- The **root title** comes from the Deposit's name (falling back to `[Untitled]`), held as a MODS title in `DMD_PHYS_ROOT`.
- Three directories always exist: `objects/` (the payload), `metadata/` (pipeline tool output) and `metadata/ad-hoc/` (arbitrary user-supplied metadata files).
- Directory divs reference dmdSecs (`DMD_metadata`, `DMD_objects`, …) that **do not exist yet** — descriptive metadata sections are created lazily, the first time something is actually set on that resource.
- There is a single `mets:fileGrp` with `USE="OBJECTS"`; all files go in it.
- There is no `mets:structLink` and no logical structMap until they are needed.

## ID conventions

All IDs are derived from the resource's path within the deposit, with a fixed prefix per section:

| Prefix | Used for | Example |
|---|---|---|
| `PHYS_` | `mets:div` in the physical structMap | `PHYS_objects/photo.tif` |
| `FILE_` | `mets:file` in the fileSec | `FILE_objects/photo.tif` |
| `ADM_`  | `mets:amdSec` | `ADM_objects/photo.tif` |
| `TECH_` | `mets:techMD` inside the amdSec | `TECH_objects/photo.tif` |
| `DMD_`  | `mets:dmdSec` | `DMD_objects/photo.tif` |
| `digiprovMD_ClamAV_` | `mets:digiprovMD` holding a virus-scan event | `digiprovMD_ClamAV_ADM_objects/photo.tif` |

The root div is always `PHYS_ROOT` with label `__ROOT`, and its descriptive metadata is `DMD_PHYS_ROOT`. Logical structMap divs have caller-supplied IDs (conventionally `LOG_0000`, `LOG_0001`, …) and their dmdSecs are `DMD_` + div ID (e.g. `DMD_LOG_0001`).

This convention makes the METS *readable* by path: a human looking at the file can find everything about `objects/photo.tif` at a glance. The platform itself no longer relies on it — since issue #188 step 1 it navigates by a path cache built from `premis:originalName` (directories) and `FLocat/@xlink:href` (files), treating ID text as opaque. See [METS identifiers](./02d-METS-Identifiers.md).

> [!NOTE]
> These IDs contain `/`, and can contain spaces and other characters not valid in XML NCNames — they are not schema-valid `xsd:ID` values. This is a known issue (#188 in the digital-preservation repo). Step 1 of the fix (ID-independent navigation) and its IDREFS companion have landed; the remaining step mints NCName-safe IDs via `XmlConvert.EncodeLocalName` for *newly written* entries, while every existing file keeps its current IDs and remains fully readable and editable. The shape described here (prefix + identifier) is stable; the exact encoding of the path part will change. Full story: [METS identifiers](./02d-METS-Identifiers.md).

## Physical structMap

The physical structMap mirrors the deposit's directory tree exactly.

- Directories are `<mets:div TYPE="Directory">` with a `LABEL` (a human-readable name, editable independently of the path), an `ADMID` and — once any descriptive metadata is set — a `DMDID`.
- Files are `<mets:div TYPE="Item">` containing exactly one `<mets:fptr FILEID="FILE_{path}"/>`. The `LABEL` is the file's display name, which defaults to the filename but can be changed (e.g. `LABEL="Tape 1 Side 1"` for `tape1side1.wav`).
- Children of a div are kept **sorted alphabetically by label** (case-insensitive); adding a file re-sorts its siblings.
- A file or directory can only be added when its parent directory already exists in the METS; deletes are only permitted on files and *empty* directories.

A populated example:

```xml
<mets:structMap TYPE="PHYSICAL">
  <mets:div ID="PHYS_ROOT" LABEL="__ROOT" DMDID="DMD_PHYS_ROOT" TYPE="Directory">
    <mets:div ID="PHYS_metadata" LABEL="metadata" DMDID="DMD_metadata" ADMID="ADM_metadata" TYPE="Directory">
      <mets:div ID="PHYS_metadata/ad-hoc" LABEL="ad-hoc" DMDID="DMD_metadata/ad-hoc"
                ADMID="ADM_metadata/ad-hoc" TYPE="Directory" />
    </mets:div>
    <mets:div ID="PHYS_objects" LABEL="objects" DMDID="DMD_objects" ADMID="ADM_objects" TYPE="Directory">
      <mets:div ID="PHYS_objects/amber-rudd.m4a" LABEL="Amber Rudd.m4a" TYPE="Item">
        <mets:fptr FILEID="FILE_objects/amber-rudd.m4a" />
      </mets:div>
      <mets:div ID="PHYS_objects/angela-eagle.m4a" LABEL="Angela Eagle.m4a" TYPE="Item"
                DMDID="DMD_objects/angela-eagle.m4a">
        <mets:fptr FILEID="FILE_objects/angela-eagle.m4a" />
      </mets:div>
    </mets:div>
  </mets:div>
</mets:structMap>
```

Note that `DMDID` appears on the file div only when that file actually has descriptive metadata (here, `angela-eagle.m4a` has its own access conditions — see below).

## fileSec

One file group, `USE="OBJECTS"`. Each file entry carries its content type and points at its administrative metadata:

```xml
<mets:fileSec>
  <mets:fileGrp USE="OBJECTS">
    <mets:file ID="FILE_objects/photo.tif" MIMETYPE="image/tiff" ADMID="ADM_objects/photo.tif">
      <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/photo.tif" />
    </mets:file>
  </mets:fileGrp>
</mets:fileSec>
```

- `xlink:href` is the path of the file **relative to the METS file's own directory** — for a `RootLevel` deposit that is the deposit root, for a `BagIt` deposit it is the `data/` directory. Paths in the METS never include the `data/` prefix.
- `MIMETYPE` is the best content type we have — the value supplied at upload, refined by format identification when the pipeline runs. It is omitted when the type is not identified.
- The METS file **never describes itself**: there is no `mets:file` entry for `mets.xml`. (The parser adds a synthetic entry for it when reading, so downstream code still sees it in the file list.)

## Technical metadata: amdSec / techMD / PREMIS object

Every file and every directory has one `mets:amdSec` containing one `mets:techMD` wrapping a PREMIS 3 `premis:object` of type `premis:file`, `MDTYPE="PREMIS:OBJECT"`.

For a **directory**, the PREMIS object is minimal — it exists to anchor the directory's path in `premis:originalName`:

```xml
<mets:amdSec ID="ADM_objects">
  <mets:techMD ID="TECH_objects">
    <mets:mdWrap MDTYPE="PREMIS:OBJECT">
      <mets:xmlData>
        <premis:object xsi:type="premis:file">
          <premis:objectCharacteristics />
          <premis:originalName>objects</premis:originalName>
        </premis:object>
      </mets:xmlData>
    </mets:mdWrap>
  </mets:techMD>
</mets:amdSec>
```

For a **file**, the PREMIS object accumulates everything we learn about it. A fully populated example (an image that has been through the pipeline):

```xml
<mets:amdSec ID="ADM_objects/photo.tif">
  <mets:techMD ID="TECH_objects/photo.tif">
    <mets:mdWrap MDTYPE="PREMIS:OBJECT">
      <mets:xmlData>
        <premis:object xsi:type="premis:file">
          <premis:significantProperties>
            <premis:significantPropertiesType>ImageWidth</premis:significantPropertiesType>
            <premis:significantPropertiesValue>4032</premis:significantPropertiesValue>
          </premis:significantProperties>
          <premis:significantProperties>
            <premis:significantPropertiesType>ImageHeight</premis:significantPropertiesType>
            <premis:significantPropertiesValue>3024</premis:significantPropertiesValue>
          </premis:significantProperties>
          <premis:objectCharacteristics>
            <premis:fixity>
              <premis:messageDigestAlgorithm xsi:type="premis:messageDigestAlgorithm">SHA256</premis:messageDigestAlgorithm>
              <premis:messageDigest>eb634d64ce8e6be5195174ceaef9ac9e19c37119f3b31618630aa633ccdbf68f</premis:messageDigest>
            </premis:fixity>
            <premis:size>9876543</premis:size>
            <premis:format>
              <premis:formatDesignation>
                <premis:formatName xsi:type="premis:formatName">Tagged Image File Format</premis:formatName>
              </premis:formatDesignation>
              <premis:formatRegistry>
                <premis:formatRegistryName xsi:type="premis:formatRegistryName">PRONOM</premis:formatRegistryName>
                <premis:formatRegistryKey xsi:type="premis:formatRegistryKey">fmt/353</premis:formatRegistryKey>
              </premis:formatRegistry>
            </premis:format>
            <premis:objectCharacteristicsExtension xsi:type="premis:objectCharacteristicsExtension">
              <ExifMetadata>
                <ImageHeight>3024</ImageHeight>
                <ImageWidth>4032</ImageWidth>
              </ExifMetadata>
            </premis:objectCharacteristicsExtension>
          </premis:objectCharacteristics>
          <premis:originalName>objects/photo.tif</premis:originalName>
        </premis:object>
      </mets:xmlData>
    </mets:mdWrap>
  </mets:techMD>
</mets:amdSec>
```

Element by element:

| Element | Meaning | Written when |
|---|---|---|
| `premis:fixity` | SHA256 digest, algorithm always written as `SHA256` | On upload (client-supplied digest) and verified/updated by tools |
| `premis:size` | Size in bytes | On upload |
| `premis:format` | PRONOM identification: human-readable `formatName` plus `formatRegistry` PRONOM / key (`fmt/353`) | When Siegfried (via Brunnhilde) has identified the format |
| `premis:originalName` | The file's deposit-relative path | Always |
| `premis:storage` / `premis:contentLocation` | A URI locating the binary in preservation storage; `storageMedium` is set to our agent name so we can find our own storage assertion among others | When known (e.g. METS exported from an Archival Group) |
| `premis:significantProperties` | Typed name/value pairs — see next section | When tool output or client metadata provides them |
| `premis:objectCharacteristicsExtension` | Raw Exif dump — see next section | When Exif extraction has run |

Updates are **patches, not rewrites**: setting a new digest, size or format only touches those elements; anything else already in the PREMIS object (including `significantProperties` from other sources) is preserved.

### Significant properties: extents

Media extents are written as PREMIS significant properties with these type names:

- `ImageWidth`, `ImageHeight` — pixel dimensions (images and video)
- `Duration` — audio/video duration
- `Bitrate` — audio bitrate

They can arrive from two directions — extracted from Exif tool output, or asserted by the client as extent metadata — and both are merged into the same elements. If a property is asserted twice with *different* values (e.g. Exif says one width, the client says another), the write fails with a conflict error rather than silently overwriting.

For video, the Exif-derived dimensions prefer the composite `ImageSize` tag, then `SourceImageWidth`/`SourceImageHeight`, then the first `ImageWidth`/`ImageHeight` — per-track tags in containers like MOV can be misleading (a timecode track reporting 853×20).

### Exif extension blob

The complete Exif tool output is preserved as an XML blob inside `premis:objectCharacteristicsExtension`, under an `<ExifMetadata>` element with one child element per tag (tag names stripped to alphanumerics):

```xml
<premis:objectCharacteristicsExtension xsi:type="premis:objectCharacteristicsExtension">
  <ExifMetadata>
    <Duration>3:42</Duration>
    <AvgBitrate>128 kbps</AvgBitrate>
  </ExifMetadata>
</premis:objectCharacteristicsExtension>
```

Re-running Exif replaces this blob wholesale (it does not merge), but leaves significant properties from other sources alone.

### Virus scanning: digiprovMD / PREMIS event

Virus scan results are a PREMIS *event*, not part of the object. They live in a `mets:digiprovMD` in the same amdSec as the file's techMD, with `MDTYPE="PREMIS:EVENT"` and the ID convention `digiprovMD_ClamAV_{admId}`:

```xml
<mets:digiprovMD ID="digiprovMD_ClamAV_ADM_objects/photo.tif">
  <mets:mdWrap MDTYPE="PREMIS:EVENT">
    <mets:xmlData>
      <premis:event>
        <premis:eventType>virus check</premis:eventType>
        <premis:eventDateTime>16 June 2026</premis:eventDateTime>
        <premis:eventDetailInformation>
          <premis:eventDetail>ClamAV 1.4.3/27932/Fri Mar  6 07:24:27 2026</premis:eventDetail>
        </premis:eventDetailInformation>
        <premis:eventOutcomeInformation>
          <premis:eventOutcome>Pass</premis:eventOutcome>
          <premis:eventOutcomeDetail />
        </premis:eventOutcomeInformation>
      </premis:event>
    </mets:xmlData>
  </mets:mdWrap>
</mets:digiprovMD>
```

- `eventDetail` records the scanner and virus-definition versions.
- `eventOutcome` is `Pass` or `Fail`; on `Fail`, `eventOutcomeDetail/eventOutcomeDetailNote` names the virus found.
- Re-scanning patches the existing event in place.

## Descriptive metadata: dmdSec / MODS

All descriptive metadata is MODS, wrapped in `mets:dmdSec` with `MDTYPE="MODS"`, and always attached to a `mets:div` (physical or logical) via `DMDID` — never to a `mets:file`.

We deliberately use a *small* MODS vocabulary. The platform is not a catalogue; rich descriptive metadata lives in external systems and is referenced by identifier.

### Title

```xml
<mods:titleInfo>
  <mods:title>Women of Westminster</mods:title>
</mods:titleInfo>
```

The root div's title is the name of the Archival Group. Logical structMap divs get titles too (see below).

### Access restrictions

Zero or more `mods:accessCondition` elements with `type="restriction on access"`. The values are access-control tokens meaningful to downstream delivery systems (not to the preservation platform itself):

```xml
<mods:accessCondition type="restriction on access" xlink:type="simple">Level1</mods:accessCondition>
```

Setting access restrictions replaces all existing `restriction on access` elements for that div; setting an empty list clears them.

### Rights statement

At most one `mods:accessCondition` with `type="use and reproduction"`, whose value is a rights URI:

```xml
<mods:accessCondition type="use and reproduction" xlink:type="simple">https://rightsstatements.org/vocab/NoC-NC/1.0/</mods:accessCondition>
```

There are three distinct states, because rights are *inherited* down the physical tree when read back (see the [parsing page](./02c-METS-Parsing.md#effective-metadata-inheritance)):

1. **Set** — the element holds a rights URI.
2. **Absent** — no element; the resource inherits its parent's rights.
3. **Explicitly none** — the element is present with the non-URI sentinel value `null`. This *suppresses inheritance*: the resource is positively asserted to have no rights statement, and does not pick up its parent's.

```xml
<!-- state 3: this file must NOT inherit the parent's rights statement -->
<mods:accessCondition type="use and reproduction" xlink:type="simple">null</mods:accessCondition>
```

### Catalogue record identifiers

`mods:recordInfo` holds one or more `mods:recordIdentifier` elements, each with a `source` attribute naming the identifying system:

```xml
<mods:recordInfo>
  <mods:recordIdentifier source="identity-service">b6n9e4c2</mods:recordIdentifier>
  <mods:recordIdentifier source="EMu">MS 2249</mods:recordIdentifier>
</mods:recordInfo>
```

This is how a deposit (or a logical range within it — an individual interview, say) is linked to catalogue records and to the Leeds Identity Service PID. Setting record info replaces the whole `recordInfo`; setting one with an empty identifier list clears it.

### Lazy creation and pruning

dmdSecs are created only when metadata is first set on a div — which is why the skeleton has dangling `DMDID` references. Symmetrically, when clearing metadata leaves a MODS record completely empty, the wrapping dmdSec is removed and the `DMDID` reference dropped — *unless* the dmdSec carries anything beyond the MODS we manage (an `mdRef`, `GROUPID`, `STATUS`, `ADMID` or extension attributes), in which case it is left intact.

## Logical structMaps

Logical structure — the intellectual arrangement of the content, as distinct from its file layout — is expressed as one or more `<mets:structMap TYPE="LOGICAL">` elements. Each logical structMap has a single root div and represents an independent structure (the platform supports several per METS, and their document order is significant and settable).

Each div in a logical structMap:

- has an `ID` (stable, caller-supplied), a `TYPE` (freeform: `Collection`, `Item`, `Range`…) and a `LABEL`;
- may have a `DMDID` pointing at a MODS dmdSec carrying its title, record identifiers, access restrictions and rights, exactly as described above (the dmdSec ID is `DMD_{divId}`);
- contains child divs and/or `mets:fptr` file pointers.

```xml
<mets:structMap TYPE="LOGICAL">
  <mets:div ID="LOG_0000" LABEL="Women of Westminster" TYPE="Collection" DMDID="DMD_LOG_0000">
    <mets:div ID="LOG_0001" LABEL="Amber Rudd" TYPE="Item" DMDID="DMD_LOG_0001">
      <mets:fptr FILEID="FILE_objects/amber-rudd.m4a" />
      <mets:fptr FILEID="FILE_objects/amber-rudd.docx" />
    </mets:div>
    <mets:div ID="LOG_0002" LABEL="Angela Eagle" TYPE="Item" DMDID="DMD_LOG_0002">
      <mets:fptr FILEID="FILE_objects/angela-eagle-redacted.m4a" />
      <mets:fptr FILEID="FILE_objects/angela-eagle-transcript.docx" />
    </mets:div>
  </mets:div>
</mets:structMap>
```

Replacing a logical structMap (matched by root div ID) removes the old one *and* the dmdSecs it referenced, then writes the new tree; removing one cleans up its dmdSecs the same way. The physical structMap is never affected.

### File pointers: whole files, time segments, image regions

A logical div can point at content in four ways:

**Whole file** — a plain fptr:

```xml
<mets:fptr FILEID="FILE_objects/amber-rudd.m4a" />
```

**Time segment** — for AV content, a `mets:area` with `BETYPE="TIME"`. `BEGIN`/`END` are `HH:MM:SS` or `HH:MM:SS.sss` time codes. This is how, for example, one side of an oral-history tape is divided into individual interviews:

```xml
<mets:div ID="LOG_0002" LABEL="AITCHISON, BERTRAM STEWART" TYPE="Item" DMDID="DMD_LOG_0002">
  <mets:fptr>
    <mets:area FILEID="FILE_objects/tape1side1.wav" BETYPE="TIME" BEGIN="00:36:40" END="00:45:00" />
  </mets:fptr>
  <mets:fptr>
    <mets:area FILEID="FILE_objects/tape1side2.wav" BETYPE="TIME" BEGIN="00:00:09.2" END="00:20:09" />
  </mets:fptr>
</mets:div>
```

(A single logical item spanning two physical files — the interview continues on the other side of the tape.)

**Image region** — a `mets:area` with `SHAPE="RECT"` and `COORDS="x1,y1,x2,y2"` (top-left and bottom-right corners in pixels):

```xml
<mets:fptr>
  <mets:area FILEID="FILE_objects/map.tif" SHAPE="RECT" COORDS="0,2000,6000,4000" />
</mets:fptr>
```

**Combined** — one area may carry both temporal and spatial attributes (a region of a video for a time window):

```xml
<mets:fptr>
  <mets:area FILEID="FILE_objects/video.mp4" SHAPE="RECT" COORDS="10,20,100,200"
             BEGIN="00:03:57" END="00:04:10" BETYPE="TIME" />
</mets:fptr>
```

`RECT` is the only shape we write; `CIRCLE` and `POLY` are not supported. Area attributes we read from an existing METS but don't model (an unrecognised `BETYPE` such as `BYTE`, or an unsupported shape) are preserved verbatim and written back unchanged on round-trip, so we never destroy a third party's area semantics by editing.

## File-to-file links: structLink

Relationships between files — this transcript belongs to that audio recording — are `mets:smLink` elements in the `mets:structLink` section. `xlink:from` and `xlink:to` are `FILE_` IDs, and `xlink:arcrole` is a URI describing the relationship. We use the IIIF Presentation 3 motivation/`provides` vocabulary:

```xml
<mets:structLink>
  <mets:smLink xlink:from="FILE_objects/amber-rudd.m4a"
               xlink:to="FILE_objects/amber-rudd.docx"
               xlink:arcrole="http://iiif.io/api/presentation/3#transcript" />
</mets:structLink>
```

Known roles (all in the `http://iiif.io/api/presentation/3#` namespace): `transcript`, `translation`, `closedCaptions`, `alternativeText`, `longDescription`, `highContrastAudio`, `highContrastDisplay`, and the generic fallback `supplementing`.

The iiif-builder uses these links to attach supplementing annotations to the right canvases. The `structLink` section only exists once the first link is written.

> [!NOTE]
> `mets:smLink` is also the mechanism Goobi uses to join its *logical* divs to its *physical* divs. We can read that style (see the parsing page) but never write it — in our METS, logical divs point at files directly with `mets:fptr`, and `structLink` is reserved for file-to-file relationships carrying an `arcrole`.

## BagIt deposits

For a Deposit created with the `BagIt` template, the layout on disk/S3 is a BagIt bag: payload under `data/`, tag files (`bagit.txt`, `manifest-sha256.txt`, …) at the root. The managed METS file lives at `data/mets.xml`, and everything in this specification applies *relative to the `data/` directory*: `xlink:href` values, `premis:originalName` values and path-derived IDs never include the `data/` prefix. The `objects/`, `metadata/` and `metadata/ad-hoc/` folders sit inside `data/`.

## A complete example

Putting it all together — an oral-history collection with audio, transcripts, per-file access overrides, logical structure and file links (abbreviated; every file has an amdSec like those shown earlier):

```xml
<mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:mods="http://www.loc.gov/mods/v3"
           xmlns:premis="http://www.loc.gov/premis/v3" xmlns:xlink="http://www.w3.org/1999/xlink"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <mets:metsHdr CREATEDATE="2025-11-10T11:28:24+00:00">
    <mets:agent ROLE="CREATOR" TYPE="OTHER" OTHERTYPE="SOFTWARE">
      <mets:name>University of Leeds Digital Library Infrastructure Project</mets:name>
    </mets:agent>
  </mets:metsHdr>

  <!-- Title of the whole Archival Group -->
  <mets:dmdSec ID="DMD_PHYS_ROOT">
    <mets:mdWrap MDTYPE="MODS"><mets:xmlData><mods:mods>
      <mods:titleInfo><mods:title>Women of Westminster</mods:title></mods:titleInfo>
    </mods:mods></mets:xmlData></mets:mdWrap>
  </mets:dmdSec>

  <!-- Access policy and identifiers for the content, set on objects/ so all files inherit -->
  <mets:dmdSec ID="DMD_objects">
    <mets:mdWrap MDTYPE="MODS"><mets:xmlData><mods:mods>
      <mods:accessCondition type="restriction on access" xlink:type="simple">Level1</mods:accessCondition>
      <mods:accessCondition type="use and reproduction" xlink:type="simple">http://rightsstatements.org/vocab/InC/1.0/</mods:accessCondition>
      <mods:recordInfo>
        <mods:recordIdentifier source="identity-service">b6n9e4c2</mods:recordIdentifier>
        <mods:recordIdentifier source="EMu">MS 2249</mods:recordIdentifier>
      </mods:recordInfo>
    </mods:mods></mets:xmlData></mets:mdWrap>
  </mets:dmdSec>

  <!-- Descriptive metadata for a logical range: one interview -->
  <mets:dmdSec ID="DMD_LOG_0001">
    <mets:mdWrap MDTYPE="MODS"><mets:xmlData><mods:mods>
      <mods:titleInfo><mods:title>Interview with Amber Rudd</mods:title></mods:titleInfo>
      <mods:recordInfo>
        <mods:recordIdentifier source="identity-service">mg56cva7</mods:recordIdentifier>
        <mods:recordIdentifier source="EMu">MS 2249/1</mods:recordIdentifier>
      </mods:recordInfo>
    </mods:mods></mets:xmlData></mets:mdWrap>
  </mets:dmdSec>

  <!-- A file-level override: closed, and explicitly no rights statement -->
  <mets:dmdSec ID="DMD_objects/angela-eagle.m4a">
    <mets:mdWrap MDTYPE="MODS"><mets:xmlData><mods:mods>
      <mods:accessCondition type="restriction on access" xlink:type="simple">Closed</mods:accessCondition>
      <mods:accessCondition type="use and reproduction" xlink:type="simple">null</mods:accessCondition>
    </mods:mods></mets:xmlData></mets:mdWrap>
  </mets:dmdSec>

  <!-- amdSecs: one per directory and per file (fixity, size, PRONOM format, originalName) ... -->

  <mets:fileSec>
    <mets:fileGrp USE="OBJECTS">
      <mets:file ID="FILE_objects/amber-rudd.m4a" MIMETYPE="audio/m4a" ADMID="ADM_objects/amber-rudd.m4a">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/amber-rudd.m4a" />
      </mets:file>
      <mets:file ID="FILE_objects/amber-rudd.docx" MIMETYPE="application/msword" ADMID="ADM_objects/amber-rudd.docx">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/amber-rudd.docx" />
      </mets:file>
      <!-- ... -->
    </mets:fileGrp>
  </mets:fileSec>

  <mets:structMap TYPE="PHYSICAL">
    <mets:div ID="PHYS_ROOT" LABEL="__ROOT" DMDID="DMD_PHYS_ROOT" TYPE="Directory">
      <mets:div ID="PHYS_metadata" LABEL="metadata" DMDID="DMD_metadata" ADMID="ADM_metadata" TYPE="Directory" />
      <mets:div ID="PHYS_objects" LABEL="objects" DMDID="DMD_objects" ADMID="ADM_objects" TYPE="Directory">
        <mets:div ID="PHYS_objects/amber-rudd.m4a" LABEL="Amber Rudd.m4a" TYPE="Item">
          <mets:fptr FILEID="FILE_objects/amber-rudd.m4a" />
        </mets:div>
        <mets:div ID="PHYS_objects/angela-eagle.m4a" LABEL="Angela Eagle.m4a" TYPE="Item"
                  DMDID="DMD_objects/angela-eagle.m4a">
          <mets:fptr FILEID="FILE_objects/angela-eagle.m4a" />
        </mets:div>
        <!-- ... -->
      </mets:div>
    </mets:div>
  </mets:structMap>

  <mets:structMap TYPE="LOGICAL">
    <mets:div ID="LOG_0000" LABEL="Women of Westminster" TYPE="Collection" DMDID="DMDLOG_0000">
      <mets:div ID="LOG_0001" LABEL="Amber Rudd" TYPE="Item" DMDID="DMD_LOG_0001">
        <mets:fptr FILEID="FILE_objects/amber-rudd.m4a" />
        <mets:fptr FILEID="FILE_objects/amber-rudd.docx" />
      </mets:div>
      <!-- ... -->
    </mets:div>
  </mets:structMap>

  <mets:structLink>
    <mets:smLink xlink:from="FILE_objects/amber-rudd.m4a" xlink:to="FILE_objects/amber-rudd.docx"
                 xlink:arcrole="http://iiif.io/api/presentation/3#supplementing" />
  </mets:structLink>
</mets:mets>
```

From this single file the iiif-builder can construct a IIIF manifest with ranges (from the logical structMap), canvases (from files or time segments), supplementing annotations (from structLink), labels and metadata (from MODS), and access/rights information — and the Preservation API can validate the deposit's completeness and generate diff import jobs (from fixity, size and paths).
