# The Preservation API's use of METS files

The Preservation API is aware of METS and will try to read METS files in Deposits and Archival Groups, and, where a Deposit is created from a template or has a METS file with a particular mets:Agent, will write to the METS file as you edit the Deposit, generate tool output data, and other operations.

The aim is that the Preservation API can read METS from a variety of sources, not just the METS files it creates and manages. When a new profile of METS is used, that it can't extract the necessary information from, the maintainers of the API should extend it to understand that profile.

## Parsing strategy

The parser does not need to establish a complete representation of the METS as it only needs certain information about the files and some of their metadata. It can accomodate variation in how different METS file are produced.

It starts at first the _Physical_ structMap. If no `mets:structMap` is found with the TYPE attribute "physical" (case-insensitive), then it picks the first structMap (of any type).

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
        <mets:file ID="file-23eacb1b-d9d3-4181-9601-c10dc8a23a48" GROUPID="Group-23eacb1b-d9d3-4181-9601-c10dc8a23a48" ADMID="amdSec_1">
            <mets:FLocat xlink:href="objects/Edgware_Community_Hospital/03_05_01.tif" LOCTYPE="OTHER" OTHERLOCTYPE="SYSTEM" />
        </mets:file>
        ...        
        <mets:file ID="file-6158701f-4993-4016-82cc-ec5dbdc99e3e" GROUPID="Group-6158701f-4993-4016-82cc-ec5dbdc99e3e" ADMID="amdSec_2">
            <mets:FLocat xlink:href="objects/Edgware_Community_Hospital/03_05_02.tif" LOCTYPE="OTHER" OTHERLOCTYPE="SYSTEM" />
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
  <mets:fileGrp USE="reference">
    <mets:file ID="eprint_10315_370442" SIZE="266035584" MIMETYPE="image/jpeg" ADMID="AMD_eprint_10315_370442">
      <mets:FLocat LOCTYPE="URL" xlink:type="simple" xlink:href="objects/372705s_002.jpg"/>
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
        <mets:div ADMID="AMD_0002" ID="PHYS_0002" ORDER="2" ORDERLABEL=" - " TYPE="page">
            <mets:fptr FILEID="FILE_0002_OBJECTS" />
            <mets:fptr FILEID="FILE_0002_ALTO" />
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

## Parsing structMap and fileSec

If a child `mets:div` contains `mets:fptr` as immediate children, or it has `TYPE="directory"`, it is considered a Directory. In the Goobi example above the `<mets:div TYPE="physSequence">` is skipped over and doesn't contribute a directory to the parsed tree. The parser finds the `mets:file` elements and determines the relative path from the `xlink:href` attribute. The complete set of actual file paths on disk yield a physical structure which is then augmented by any additional information derived from the physical structMap. Thus in the Goobi example we know that there are two directories `alto/` and `objects/` each with files in them.

The parser tries to find the most appropriate `mets:techMD` element for each file by navigating the ADMID closest to the file. In the Goobi example above the `ADMID` attribute belongs to a `mets:div` containing two files; we assume that the the techMD applies to the first file in this case.

> [!NOTE]
> An alternative strategy could be to decide based on `<mets:fileGrp USE="OBJECTS">` as the parent - where "OBJECTS" takes precedence as the file of interest over any other value of `USE`.

Where the `MIMETYPE` attribute is present on a `mets:file` element, we parse that as the content type.


## Premis objects

Once the appropriate `mets:techMD` element for a file is found, the parser looks for a `premis:object` _preferably_ of type file. Again, this can take different forms:

### Archivematica PREMIS object

```xml
<mets:techMD ID="techMD_2">
    <mets:mdWrap MDTYPE="PREMIS:OBJECT">
        <mets:xmlData>
            <premis:object xmlns:premis="http://www.loc.gov/premis/v3" xsi:type="premis:file" xsi:schemaLocation="http://www.loc.gov/premis/v3 http://www.loc.gov/standards/premis/v3/premis.xsd" version="3.0">
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
                            <premis:formatVersion></premis:formatVersion>
                        </premis:formatDesignation>
                        <premis:formatRegistry>
                            <premis:formatRegistryName>PRONOM</premis:formatRegistryName>
                            <premis:formatRegistryKey>fmt/353</premis:formatRegistryKey>
                        </premis:formatRegistry>
                    </premis:format>
                    <premis:creatingApplication>
                        <premis:dateCreatedByApplication>2024-03-13T13:54:27Z</premis:dateCreatedByApplication>
                    </premis:creatingApplication>
                    <premis:objectCharacteristicsExtension>
                        ...
                    </premis:objectCharacteristicsExtension>
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
    <premis:object xsi:type="premis:file" xsi:schemaLocation="http://www.loc.gov/premis/v3 http://www.loc.gov/standards/premis/v3/premis.xsd">
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

### Goobi PREMIS object

```xml
<mets:techMD ID="AMD_0001">
    <mets:mdWrap MDTYPE="OTHER" MIMETYPE="text/xml">
        <mets:xmlData>
            <premis:object version="3.0" xsi:schemaLocation="http://www.loc.gov/premis/v3 http://www.loc.gov/standards/premis/v3/premis.xsd" xsi:type="premis:file">
                <premis:objectIdentifier>
                    <premis:objectIdentifierType>local</premis:objectIdentifierType>
                    <premis:objectIdentifierValue>b29356350_0001.jp2</premis:objectIdentifierValue>
                </premis:objectIdentifier>
                <premis:objectIdentifier>
                    <premis:objectIdentifierType>uuid</premis:objectIdentifierType>
                    <premis:objectIdentifierValue>8f36b42a-99b6-40f7-b749-a62e3c297faa</premis:objectIdentifierValue>
                </premis:objectIdentifier>
                <premis:significantProperties>
                    <premis:significantPropertiesType>ImageHeight</premis:significantPropertiesType>
                    <premis:significantPropertiesValue>4325</premis:significantPropertiesValue>
                </premis:significantProperties>
                <premis:significantProperties>
                    <premis:significantPropertiesType>ImageWidth</premis:significantPropertiesType>
                    <premis:significantPropertiesValue>2513</premis:significantPropertiesValue>
                </premis:significantProperties>
                <premis:objectCharacteristics>
                    <premis:compositionLevel />
                    <premis:fixity>
                        <premis:messageDigestAlgorithm>sha256</premis:messageDigestAlgorithm>
                        <premis:messageDigest>6eb6c17cd93e392fed8e1cb4d9de5617b8a9b4de</premis:messageDigest>
                    </premis:fixity>
                    <premis:size>1348420</premis:size>
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

## Reading the PREMIS object

Although the surrounding XML differs, each of these `premis:object` sections have the same schema. They are all parsed for digest information (specifically a SHA256 digest) and file format information.



