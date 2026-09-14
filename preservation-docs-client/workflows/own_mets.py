"""
Writing your own METS file.

Shared by the workflow samples that supply their own METS rather than letting the platform manage
one. Not a sample in its own right.

This is about the smallest document the platform will accept as a description of a deposit. It has
to give, for every file:

  * a path, in `mets:FLocat/@xlink:href`, relative to the directory the METS file sits in;
  * a SHA256 digest, as `premis:fixity` in a `mets:techMD` the file's ADMID points at;
  * a size, as `premis:size` in the same place;
  * a content type, in `mets:file/@MIMETYPE`.

The digest, size and content type must agree with the file that is actually in the workspace, or
the Import Job diff will refuse to be generated. Directories are inferred from the paths, so there
is nothing to declare for `objects/` itself.

Note what is NOT here: the METS file does not describe itself. The platform adds it to the object,
with a digest it takes from storage.

The `mets:agent` says who wrote the document. Because it is not the platform's own name, the
platform will read this METS but never write to it - see the METS editability page. That is the
point of this workflow: the METS is yours.
"""
import mimetypes
from datetime import datetime, timezone
from xml.sax.saxutils import escape, quoteattr

AGENT_NAME = "preservation-docs-samples"

TECH_MD = """    <mets:techMD ID="{tech_id}">
      <mets:mdWrap MDTYPE="OTHER" MIMETYPE="text/xml">
        <mets:xmlData>
          <premis:object xsi:type="premis:file">
            <premis:objectIdentifier>
              <premis:objectIdentifierType>local</premis:objectIdentifierType>
              <premis:objectIdentifierValue>{path}</premis:objectIdentifierValue>
            </premis:objectIdentifier>
            <premis:objectCharacteristics>
              <premis:fixity>
                <premis:messageDigestAlgorithm>SHA256</premis:messageDigestAlgorithm>
                <premis:messageDigest>{digest}</premis:messageDigest>
              </premis:fixity>
              <premis:size>{size}</premis:size>
            </premis:objectCharacteristics>
            <premis:originalName>{path}</premis:originalName>
          </premis:object>
        </mets:xmlData>
      </mets:mdWrap>
    </mets:techMD>"""

FILE_ENTRY = """      <mets:file ID="{file_id}" MIMETYPE={content_type} SIZE="{size}" ADMID="{tech_id}">
        <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href={href}/>
      </mets:file>"""

DIV = """      <mets:div TYPE="File" LABEL={name}>
        <mets:fptr FILEID="{file_id}"/>
      </mets:div>"""

DOCUMENT = """<?xml version="1.0" encoding="utf-8"?>
<mets:mets xmlns:mets="http://www.loc.gov/METS/"
           xmlns:mods="http://www.loc.gov/mods/v3"
           xmlns:premis="http://www.loc.gov/premis/v3"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <mets:metsHdr CREATEDATE="{created}">
    <mets:agent ROLE="CREATOR" TYPE="OTHER" OTHERTYPE="SOFTWARE">
      <mets:name>{agent}</mets:name>
    </mets:agent>
  </mets:metsHdr>
  <mets:dmdSec ID="DMD_OBJECT">
    <mets:mdWrap MDTYPE="MODS">
      <mets:xmlData>
        <mods:titleInfo>
          <mods:title>{title}</mods:title>
        </mods:titleInfo>
      </mets:xmlData>
    </mets:mdWrap>
  </mets:dmdSec>
  <mets:amdSec ID="AMD_OBJECT">
{tech_mds}
  </mets:amdSec>
  <mets:fileSec>
    <mets:fileGrp USE="OBJECTS">
{file_entries}
    </mets:fileGrp>
  </mets:fileSec>
  <mets:structMap TYPE="physical">
    <mets:div TYPE="Object" DMDID="DMD_OBJECT">
{divs}
    </mets:div>
  </mets:structMap>
</mets:mets>
"""


def content_type_of(local_path: str) -> str:
    """The same guess s3_helpers makes when uploading, so that METS and S3 agree."""
    return mimetypes.guess_type(local_path)[0] or "application/octet-stream"


def build_mets(title: str, files: list) -> str:
    """
    `files` is a list of dicts with keys `local_path`, `size` and `digest`, and optionally `name`
    and `content_type`. Returns the METS document as a string.
    """
    tech_mds, file_entries, divs = [], [], []

    for index, file in enumerate(files, start=1):
        tech_id = "TECH_%d" % index
        file_id = "FILE_%d" % index
        local_path = file["local_path"]
        name = file.get("name") or local_path.rsplit("/", 1)[-1]
        content_type = file.get("content_type") or content_type_of(local_path)

        tech_mds.append(TECH_MD.format(
            tech_id=tech_id, path=escape(local_path),
            digest=file["digest"], size=file["size"]))
        file_entries.append(FILE_ENTRY.format(
            file_id=file_id, tech_id=tech_id, size=file["size"],
            content_type=quoteattr(content_type), href=quoteattr(local_path)))
        divs.append(DIV.format(file_id=file_id, name=quoteattr(name)))

    return DOCUMENT.format(
        created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        agent=AGENT_NAME,
        title=escape(title),
        tech_mds="\n".join(tech_mds),
        file_entries="\n".join(file_entries),
        divs="\n".join(divs))


def files_from_filesystem(directory, found=None):
    """Turn a deposit's file system view into the list `build_mets` wants, so that an object's
    METS can be rebuilt from what is actually in the workspace. Skips files in the root - the
    METS document itself, and the platform's own `__METSlike.json` cache."""
    found = found if found is not None else []
    for file in directory["files"]:
        local_path = file["localPath"]
        if "/" not in local_path:
            continue
        found.append({
            "local_path": local_path,
            "size": file["size"],
            "digest": file["digest"],
            "name": file.get("name"),
            "content_type": file.get("contentType"),
        })
    for child in directory["directories"]:
        files_from_filesystem(child, found)
    return found
