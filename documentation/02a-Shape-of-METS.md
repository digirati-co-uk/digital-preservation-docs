

## METS obligations

This section is to be expanded - it defines where the Preservation API looks for METS, what it looks for inside METS, and where it looks for it.

For now - be assured that it will work with Goobi METS - we will make it work with whatever METS Goobi is producing as a starter requirement.

METS-carried information:

- PRONOM data for fixity
- LABEL property of attributes

> ❓ We will formally define how we expect to see the following in METS - but they are based on Wellcome METS produced by Goobi (except the Archivematica LABEL example). For now just XML snippets.

### Fixity information in Pronom

```xml
<mets:amdSec ID="AMD">
  <mets:techMD ID="AMD_0001">
    <mets:mdWrap MDTYPE="OTHER" MIMETYPE="text/xml">
      <mets:xmlData>
        <premis:object version="3.0" xsi:schemaLocation="..." xsi:type="premis:file">            
          <premis:objectCharacteristics>
            <premis:fixity>
              <premis:messageDigestAlgorithm>SHA-1</premis:messageDigestAlgorithm>
              <premis:messageDigest>5ac97693da5cd77233515b280048631b59319df6</premis:messageDigest>
```

### Original filename

> Goobi METS doesn't record this - use the name in S3; Archivematica METS records it as `LABEL` attribute on divs in physical structMap, we will do the same when we run our normalisation pipeline

TBC - Archivematica-esque example with struct divs of type File and Directory, with LABEL attributes.


### File format identification

```xml
<mets:amdSec ID="AMD">
  <mets:techMD ID="AMD_0001">
    <mets:mdWrap MDTYPE="OTHER" MIMETYPE="text/xml">
      <mets:xmlData>
        <premis:object version="3.0" ...>            
          <premis:objectCharacteristics>
            <premis:format>
              <premis:formatDesignation>
                 <premis:formatName>JP2 (JPEG 2000 part 1)</premis:formatName>
              </premis:formatDesignation>
              <premis:formatRegistry>
                 <premis:formatRegistryName>PRONOM</premis:formatRegistryName>
                 <premis:formatRegistryKey>x-fmt/392</premis:formatRegistryKey>
              </premis:formatRegistry>
            </premis:format>
```

### Content Type if possible

Goobi does it like this:

```xml
<mets:fileSec>
    <mets:fileGrp USE="OBJECTS">
      <mets:file ID="FILE_0001_OBJECTS" MIMETYPE="image/jp2">
```

Archivematica only in tool output. But we'll try to deduce that.