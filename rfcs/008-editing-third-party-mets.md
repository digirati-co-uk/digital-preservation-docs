# RFC 008: Editing METS the platform did not write

**Status: for agreement.** This paper asks Leeds to confirm three decisions about editing METS
documents that other systems created — above all the EPrints-migrated items that make up most of
production. The platform work is specified in
[METS editability](../documentation/02e-METS-Editability.md); this paper is the short version,
with a worked example of what saying yes actually does to a document.

## The situation

Leeds needs to apply **rights statements and access conditions** to preserved items whose METS was
written by EPrints, not by the platform. Today that is impossible: the platform only edits METS it
wrote itself, and everything else — however well-formed — is read-only.

We have measured the EPrints corpus against the platform's own machinery. The result: EPrints
METS contains everything the platform needs, completely and unambiguously (a real 410-file item
resolved every file with no ambiguity). What blocks editing is not missing information but unstated
convention — the EPrints documents decline to say things METS allows them to leave unsaid, such as
labelling their structure map "physical". The platform can safely *assume* those things on
reading, without changing a byte of any preserved document.

Editing is different from reading. When the platform first **saves** such a document, it will
restructure it into the platform's own documented METS shape. That is the decision with visible
consequences, and the worked example below shows exactly what changes and what does not.

## The three decisions

### Decision 1 — what is editable

| Source of the METS | Proposed status |
|---|---|
| The platform's own METS | Editable (as now) |
| **EPrints-migrated items** | **Editable.** Read under declared assumptions; restructured to the platform shape on first save |
| Archivematica | Read-only: browsable and preservable, never edited |
| Goobi | Read-only, permanently |

Goobi is read-only on principle, not because of a technical shortfall: Goobi actively re-edits its
own METS. Two systems writing one document with different models will silently corrupt each
other's work, so a document with a living external editor is never edited here — even one whose
shape looks perfect. Archivematica documents are not being edited by anyone, but they are another
system's records, structured to another system's conventions; the platform will read them as well
as it can and leave them as they are.

### Decision 2 — the first save converts the document to the platform's shape

When someone first edits an EPrints-migrated item — applying a rights statement, say — the save
does two things at once: it applies the edit, and it makes explicit the structure the original
document left implicit. From then on the document follows
[the platform's documented METS profile](../documentation/02b-METS-Written-by-the-Platform.md).

The alternative would be documents that stay EPrints-shaped until successive edits force platform
conventions in piecemeal — a hybrid that is neither EPrints' shape nor ours, and harder for any
future software (Leeds' included) to read than either. One save, one transition.

This is **not** a bulk conversion. Nothing happens to the tens of thousands of items nobody edits;
the reading assumptions cover them indefinitely. A document is only ever restructured as part of
an edit somebody chose to make — which was always going to create a new preserved version anyway.

### Decision 3 — what survives, guaranteed

The restructure adds and rearranges; it does not destroy. Specifically, in the saved document:

- **Every EPrints identifier survives, character for character.** `eprint_10315_370441` remains
  `eprint_10315_370441`. Anything of yours that refers to elements of these documents by ID keeps
  working.
- **All EPrints metadata survives**: descriptive metadata (titles, EPrints and EMu record
  identifiers), technical metadata (checksums, sizes, format identifications) — untouched, in
  place. **The platform never edits an EPrints metadata section**: when an edit sets descriptive
  metadata on a part of the document whose existing section is EPrints', the platform writes its
  own new section alongside and links both from the same place — the original stays byte for
  byte.
- **One declared repair**: EPrints omits a wrapper element (`mets:xmlData`) that the METS schema
  requires around each file's technical metadata. The first save adds the missing wrapper; the
  content inside it — the checksums and formats themselves — is preserved verbatim. This is a
  repair to where the metadata sits, not to what it says.
- **Provenance survives**: the `EPrints 3.3.15` creator agent stays in the header; the platform
  adds itself as a second, editing agent. The `premis:storage` record of each file's original
  location on the EPrints server is likewise kept — it is history, not a live address, and when
  the platform records a storage location of its own it does so in a separate element marked as
  its own assertion.
- Files themselves are not touched at all: this is a metadata edit, producing a new version of one
  XML file.

## The worked example

A real (abbreviated) EPrints-migrated document, before any edit:

```xml
<mets:mets OBJID="eprint_10315" LABEL="Eprints Item" ...>
  <mets:metsHdr CREATEDATE="2023-12-22T04:53:58Z">
    <mets:agent ROLE="CREATOR" TYPE="OTHER" OTHERTYPE="SOFTWARE">
      <mets:name>EPrints 3.3.15</mets:name>
    </mets:agent>
  </mets:metsHdr>

  <mets:dmdSec ID="DMD_eprint_10315">
    <!-- title, abstract, EPrints and EMu record identifiers -->
  </mets:dmdSec>

  <mets:amdSec ID="AMD_eprint_10315">
    <mets:techMD ID="AMD_eprint_10315_370441">
      <!-- premis:object - sha256 digest, size, PRONOM format fmt/43 -->
    </mets:techMD>
    <!-- ...one techMD per file... -->
  </mets:amdSec>

  <mets:fileSec>
    <!-- one fileGrp per file, all USE="reference" -->
    <mets:fileGrp USE="reference">
      <mets:file ID="eprint_10315_370441" MIMETYPE="image/jpeg" ADMID="AMD_eprint_10315_370441">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/372705s_001.jpg"/>
      </mets:file>
    </mets:fileGrp>
    <mets:fileGrp USE="reference">
      <mets:file ID="eprint_10315_370442" MIMETYPE="image/jpeg" ADMID="AMD_eprint_10315_370442">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/372705s_002.jpg"/>
      </mets:file>
    </mets:fileGrp>
    <!-- ... -->
  </mets:fileSec>

  <!-- no TYPE on the structMap, no TYPE or ID on the divs -->
  <mets:structMap>
    <mets:div DMDID="DMD_eprint_10315" ADMID="AMD_eprint_10315">
      <mets:div>
        <mets:fptr FILEID="eprint_10315_370441"/>
      </mets:div>
      <mets:div>
        <mets:fptr FILEID="eprint_10315_370442"/>
      </mets:div>
      <!-- ... -->
    </mets:div>
  </mets:structMap>
</mets:mets>
```

Someone now uses the platform to set an access condition and a rights statement on the item's
content. The saved document:

```xml
<mets:mets OBJID="eprint_10315" LABEL="Eprints Item" ...>
  <mets:metsHdr CREATEDATE="2023-12-22T04:53:58Z" LASTMODDATE="2026-09-02T10:14:07Z">
    <mets:agent ROLE="CREATOR" TYPE="OTHER" OTHERTYPE="SOFTWARE">
      <mets:name>EPrints 3.3.15</mets:name>                                    <!-- kept -->
    </mets:agent>
    <mets:agent ROLE="EDITOR" TYPE="OTHER" OTHERTYPE="SOFTWARE">               <!-- added -->
      <mets:name>University of Leeds Digital Library Infrastructure Project</mets:name>
    </mets:agent>
  </mets:metsHdr>

  <mets:dmdSec ID="DMD_eprint_10315">
    <!-- unchanged, byte for byte -->
  </mets:dmdSec>

  <!-- NEW: the edit itself - the access condition and rights statement,
       attached to the objects directory so every file inherits them -->
  <mets:dmdSec ID="DMD_objects">
    <mets:mdWrap MDTYPE="MODS">
      <mets:xmlData>
        <mods:mods>
          <mods:accessCondition type="restriction on access" xlink:type="simple">Open</mods:accessCondition>
          <mods:accessCondition type="use and reproduction" xlink:type="simple">https://rightsstatements.org/vocab/InC/1.0/</mods:accessCondition>
        </mods:mods>
      </mets:xmlData>
    </mets:mdWrap>
  </mets:dmdSec>

  <mets:amdSec ID="AMD_eprint_10315">
    <!-- every techMD, checksum and format identification as it was; the one change is that
         each premis:object now sits inside the mets:xmlData wrapper the schema requires -->
  </mets:amdSec>

  <!-- NEW: the objects directory, previously only implied by the file paths,
       now has the platform's standard metadata anchor -->
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

  <mets:fileSec>
    <!-- was one fileGrp per file; now one group holding the same file
         elements - IDs, links and paths unchanged -->
    <mets:fileGrp USE="OBJECTS">
      <mets:file ID="eprint_10315_370441" MIMETYPE="image/jpeg" ADMID="AMD_eprint_10315_370441">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/372705s_001.jpg"/>
      </mets:file>
      <mets:file ID="eprint_10315_370442" MIMETYPE="image/jpeg" ADMID="AMD_eprint_10315_370442">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/372705s_002.jpg"/>
      </mets:file>
      <!-- ... -->
    </mets:fileGrp>
  </mets:fileSec>

  <!-- now explicitly physical; divs typed and identified; the file divs
       sit under the objects directory, where their paths always said they were -->
  <mets:structMap TYPE="PHYSICAL">
    <mets:div ID="PHYS_ROOT" LABEL="__ROOT" TYPE="Directory"
              DMDID="DMD_eprint_10315" ADMID="AMD_eprint_10315">               <!-- references kept -->
      <mets:div ID="PHYS_objects" LABEL="objects" TYPE="Directory"
                DMDID="DMD_objects" ADMID="ADM_objects">
        <mets:div ID="PHYS_objects_x002F_372705s_001.jpg" LABEL="372705s_001.jpg" TYPE="Item">
          <mets:fptr FILEID="eprint_10315_370441"/>                            <!-- reference kept -->
        </mets:div>
        <mets:div ID="PHYS_objects_x002F_372705s_002.jpg" LABEL="372705s_002.jpg" TYPE="Item">
          <mets:fptr FILEID="eprint_10315_370442"/>
        </mets:div>
        <!-- ... -->
      </mets:div>
    </mets:div>
  </mets:structMap>
</mets:mets>
```

Reading the differences:

- **Added**: the second agent; the new dmdSec carrying the edit; the `objects` directory's
  amdSec; `TYPE` and `ID` attributes on the structMap and its divs (the divs had no IDs before, so
  nothing was renamed — the platform's own IDs were minted for elements that had none).
- **Rearranged**: the file entries, previously in one group per file, sit in a single `OBJECTS`
  group; the file divs sit under the `objects` directory div. The elements themselves are
  unchanged.
- **Untouched**: every EPrints ID, the EPrints dmdSec, every techMD, every checksum, every file
  path, every cross-reference the original document made.

Operationally, for whoever does this work: open a deposit against the item, apply the rights
statement or access condition in the UI exactly as for a platform-native item, and preserve. The
result is a new preserved version of the item containing the updated METS; the files are
untouched; the IIIF manifest rebuilds and reflects the new access and rights. Subsequent edits to
the same item are ordinary edits of a platform-shape document.

## What we would like from Leeds

Agreement, or challenge, on the three decisions above — in particular:

1. Is the **editable set** right? (Is there any real case for editing Archivematica or Goobi
   documents that this paper dismisses too quickly?)
2. Is **restructure-on-first-save** acceptable, given the worked example? The main question to ask
   of your own systems: does anything at Leeds re-read these documents *after* preservation, in a
   way that depends on the original EPrints layout rather than on the IDs and metadata (which are
   preserved)?
3. Are the **guarantees in Decision 3** the right list? Is anything missing that your tooling
   depends on?

Building the machinery that answers "is this document editable, and what would saving change?" —
runnable in both .NET and Python — is already in progress and does not wait for this agreement;
a working checker is easier to react to than a paper. The editing capability itself ships after
the current METS identifier migration has fully bedded in.
