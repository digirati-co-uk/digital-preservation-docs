# Virus scanning and dealing with outputs

We will use ClamAV to scan deposit files for viruses as part of the pipeline.

We can either run it on its own, or via Brunnhilde. Seeing as we are already doing the latter this may be the simplest way.

The Freshclam tool should be run at least at the start of each day to update the virus definition files:

https://docs.clamav.net/manual/Usage/SignatureManagement.html

ClamAV will still run without this but will emit warnings when its definition files are more than 7 days old.

## Performance considerations

We need to see how well ClamAV works on files via the S3 Mountpoint filesystem. Whereas file format identification (Siegfried) usually just needs to read the file header, ClamAV will have to read the entire file. The local disk space that the S3 Mountpoint uses under the hood needs to accommodate this.

## Outputs

From what we have seen so far, Brunnhilde emits a file: /metadata/brunnhilde/logs/viruscheck-log.txt.

For a clean deposit, this file looks like this:

```
----------- SCAN SUMMARY -----------
Known viruses: 8707831
Engine version: 1.0.9
Scanned directories: 1
Scanned files: 1
Infected files: 0
Data scanned: 0.42 MB
Data read: 0.39 MB (ratio 1.06:1)
Time: 29.859 sec (0 m 29 s)
Start Date: 2025:09:12 09:21:57
End Date:   2025:09:12 09:22:26
Date scanned: 2025-09-12 09:21:57.081789
```

And for a found virus, the output looks like this:

```
/home/brian/Test/data/objects/virus_test_file.txt: Eicar-Signature FOUND
----------- SCAN SUMMARY -----------
Known viruses: 8707575
Engine version: 1.4.3
Scanned directories: 1
Scanned files: 2
Infected files: 1
Data scanned: 0.00 MB
Data read: 0.00 MB (ratio 0.00:1)
Time: 22.347 sec (0 m 22 s)
Start Date: 2025:09:19 10:20:10
End Date:   2025:09:19 10:20:32SS
Date scanned: 2025-09-19 10:20:10.499694
```


## Reading the virus report

WorkspaceManager (whether used by the Preservation API, Preservation UI or any other .NET application) works on a representation of the Deposit filesystem on disk/S3, in the METS, and the union of the two. We read the Deposit files and generate a tree of `WorkingDirectory` and `WorkingFile` classes, and we read the METS and generate another tree of `WorkingDirectory` and `WorkingFile` classes, and then we make a *union* of these two trees as a tree of `CombinedDirectory` and `CombinedFile`. In very simplified form:

```c#
/// The real classes are much more complex than this!

public class CombinedDirectory
{    
    public WorkingDirectory? DirectoryInDeposit;
    public WorkingDirectory? DirectoryInMets;
    
    public List<CombinedFile> Files;
    public List<CombinedDirectory> Directories;
}

public class CombinedFile
{    
    public WorkingFile? FileInDeposit;
    public WorkingFile? FileInMets;
}
```

Information from the tool outputs under /metadata is used to **decorate** the [metadata](https://github.com/uol-dlip/digital-preservation/blob/e9946dc13f2cf3e58d7237787d0b9c2cfabffe93/src/DigitalPreservation/DigitalPreservation.Common.Model/Transit/WorkingBase.cs#L36) property of `WorkingDirectory` and `WorkingFile` classes representing the filesystem:

```c#
// The base class of WorkingDirectory and WorkingFile
public abstract class WorkingBase
{
    ///....
    
    public List<Metadata> Metadata { get; set; } = [];
}
```

The class that does the work here is [MetadataReader](https://github.com/uol-dlip/digital-preservation/blob/2a4cecd3e741ba7466a36ba129f335473df69509/src/DigitalPreservation/DigitalPreservation.Workspace/MetadataReader.cs).

And similarly, information from the METS is used to **decorate** the [metadata](https://github.com/uol-dlip/digital-preservation/blob/e9946dc13f2cf3e58d7237787d0b9c2cfabffe93/src/DigitalPreservation/DigitalPreservation.Common.Model/Transit/WorkingBase.cs#L36) property of `WorkingDirectory` and `WorkingFile` classes representing the METS structure.

The class that does the work here is [MetsParser](https://github.com/uol-dlip/digital-preservation/blob/cb21241db9f3f36b310d9e31808dc960c6b9b68c/src/DigitalPreservation/Storage.Repository.Common/Mets/MetsParser.cs).

### Reading viruscheck-log.txt

The first task is to add the per-file information from the viruslog file to each WorkingFile as an `IMetadata` instance.

There is already [some stub code](https://github.com/uol-dlip/digital-preservation/blob/2a4cecd3e741ba7466a36ba129f335473df69509/src/DigitalPreservation/DigitalPreservation.Workspace/MetadataReader.cs#L70-L74) for this:

```c#

private List<string> infectedFiles = [];


private async Task FindMetadata()
{

    // ..... lots of other code omitted
    
    var brunnhildeAVResult = await storage.GetStream(brunnhildeRoot.AppendEscapedSlug("logs").AppendEscapedSlug("viruscheck-log.txt"));
    if (brunnhildeAVResult is { Success: true, Value: not null })
    {
        infectedFiles = await ReadInfectedFilePaths(brunnhildeAVResult.Value);
    }

    // ..... lots of other code omitted

}

private async Task<List<string>> ReadInfectedFilePaths(Stream stream)
{
    var txt = await GetTextFromStream(stream);
    // TODO - actually parse this once we have an infected example
    return [];
}
```

This needs to be replaced - I think `infectedFiles` isn't just a list of string file paths but instead a list of objects that can carry that "Eicar-Signature FOUND" message as well as the path.

Then, we will have a method `AddVirusScanMetadata` that does for this virus data what [AddFileFormatMetadata](https://github.com/uol-dlip/digital-preservation/blob/2a4cecd3e741ba7466a36ba129f335473df69509/src/DigitalPreservation/DigitalPreservation.Workspace/MetadataReader.cs#L147) does for the Siegfried output:

```c#

    private void AddFileFormatMetadata(SiegfriedOutput siegfriedOutput, string commonParent, string source, DateTime timestamp)
    {

        // have a look at the existing code!

    }

    private void AddVirusScanMetadata(List<???> infectedFiles, string commonParent, string source, DateTime timestamp)
    {
        // this is the new method

        foreach (var file in infectedFiles)
        {
            var localPath = file.Filename.RemoveStart(commonParent).RemoveStart("/"); // check this!
            var metadataList = GetMetadataList(localPath!);
            metadataList.Add(new VirusScanMetadata
            {
                Source = source,
                ??? = ???,
                ??? = ???
            });
        }
    }

```

We already have a [placeholder class](https://github.com/uol-dlip/digital-preservation/blob/721e322262bc0c3326aa2efdb97bfac796304737/src/DigitalPreservation/DigitalPreservation.Common.Model/Transit/Extensions/Metadata/VirusScanMetadata.cs) for Virus metadata:

```c#
public class VirusScanMetadata : Metadata
```

This class isn't doing much at the moment but is used in the UI. The actual fields of this class are ultimately dependent on:

 - what info is available
 - what we want to surface in the UI
 - what we want to write to the METS.


## Writing virus information to METS

Refer to the [example METS file](120-files/mets_am.xml). This is a Wellcome METS file generated by Archivematica. ClamAV is run as part of the pipeline.

It is extremely verbose, and we don't need all this information. (This METS file only has one actual file under /objects). But we can follow the general pattern.

You can see here the PREMIS metadata for the file AfH-25-04-06_Presentation_at_the__Embassy_of_Japan.ppt, under this path:

```
mets:mets/mets:amdSec[ID=amdSec1]/mets:techMD[ID=techMD_1]/mets:mdWrap/mets:xmlData/premis:object
```

![Premis metadata in Archivematica METS](120-files/mets_am_premis.png)


We do the same in the METS we generate, here's a DLIP-produced METS for a file in objects:

```
mets:mets/mets:amdSec[ID=ADM_objects/pxl_20250825_142937791_v17.png]/mets:techMD[ID=TECH_objects/pxl_20250825_142937791_v17.png]/mets:mdWrap/mets:xmlData/premis:object
```

![Premis metadata in DLIP METS](120-files/mets_dlip_premis.png)


Until now we haven't produced any additional sections, but it makes sense to represent the virus data in our METS the same way Archivematica does (because we can already parse Archivematica METS).

> [!IMPORTANT]
> We use a very "loose" (i.e., forgiving, flexible) parser to read METS, to accommodate different flavours of METS from different software. This is `MetsParser`. When we **write** METS - which we only do for our own METS files (we never edit an externally-produced METS) we use a much more rigid mechanism, a class library generated from the METS Schema. This class library is the [DigitalPreservation.XmlGen](https://github.com/uol-dlip/digital-preservation/tree/main/src/DigitalPreservation/DigitalPreservation.XmlGen) project in the .NET solution. The **exact** tools and commands used to produce the classes are in the [_tools](https://github.com/uol-dlip/digital-preservation/tree/main/_tools) folder.

The next task in the RFC os to describe the end result - what we want in the METS file.

Then we can join the two together in the middle.

 1. We need to read tool outputs in the Deposit under /metadata and turn them into a `VirusScanMetadata` class for each file.
 2. We need to read virus scan records in the METS file and turn them into a `VirusScanMetadata` class for each file.
 3. We also need to turn `VirusScanMetadata` instances into virus scan records in the METS file when we create or update DLIP METS.

```
filesystem / S3                                                                        METS

metadata/                  1.            CombinedFile                2.                                  
    tool_output                          /          \                              mets.xml 
           => MetadataReader       FileInDeposit    FileInMets           MetsParser <=   
                      =>  (WorkingFile::Metadata)   (WorkingFile::Metadata)  <=
                                    ||
                                     ----------------------------------  => MetsManager
                                                       3.                       => mets.xml                                         

```


### Comparison with Wellcome (temporary section)

This METS file has only one actual piece of content under objects/ - a PowerPoint file.

[mets_am.xml](120-files/mets_am.xml)

The METS refers to three other files as part of the preservation workflow, as expected, and also as expected each of them get a corresponding administrative metadata section. So in all we have 4 files each with their corresponding mets:amdSec:

```
objects/AfH-25-04-06_Presentation_at_the__Embassy_of_Japan.ppt => amdSec_1
objects/submissionDocumentation/transfer-ARTCOOB15-4947c763-5f7b-468b-9647-b22e8ac8a950/METS.xml => amdSec_4
objects/metadata/transfers/ARTCOOB15-4947c763-5f7b-468b-9647-b22e8ac8a950/rights.csv => amdSec_3
objects/metadata/transfers/ARTCOOB15-4947c763-5f7b-468b-9647-b22e8ac8a950/metadata.csv => amdSec_2
```
So far so good.

The 4 referred amdSec elements each contain one mets:techMD, one mets:rightsMD and six mets:digiprovMD metadata sections:

![METS sections in AM](120-files/am_sections.png)

The mets:techMD sections contain the PREMIS file format information, and also, in `<premis:objectCharacteristicsExtension>` all the tool outputs that Archivematica ran over each file - ExifTool, Tika, ffident and so on. So these sections are really big.

Still so far so good.

Looking at the digiprovMD sections for each file... for the three "system" files (i.e., the files not in objects/) the six digiprov events are:

- ingestion
- message digest calculation
- virus check - with output from ClamAV tool
- identify agent as Archivematica
- identify repository as wellcome
- identify user ("Admin" always it seems)

For the PowerPoint the six digiprov events are

- ingestion
- message digest calculation
- format identification
- identify agent as Archivematica
- identify repository as wellcome
- identify user ("Admin" always it seems)

So here's my question - the three "system" files get virus checked, but the powerpoint (the actual external file) does not?

There's no ClamAV output for the PowerPoint file.

I would expect it to be the other way round.

Does virus checking of the actual archive files happen before they even get to Archivematica?

Here's what the digiprov section looks like for one of the "system" files:

```xml
<mets:digiprovMD ID="digiprovMD_9">
    <mets:mdWrap MDTYPE="PREMIS:EVENT">
        <mets:xmlData>
            <premis:event xmlns:premis="http://www.loc.gov/premis/v3" xsi:schemaLocation="http://www.loc.gov/premis/v3 http://www.loc.gov/standards/premis/v3/premis.xsd" version="3.0">
                <premis:eventIdentifier>
                    <premis:eventIdentifierType>UUID</premis:eventIdentifierType>
                    <premis:eventIdentifierValue>9b46a83d-d584-4743-a209-fd3adb86da67</premis:eventIdentifierValue>
                </premis:eventIdentifier>
                <premis:eventType>virus check</premis:eventType>
                <premis:eventDateTime>2024-03-15T14:34:48.224113+00:00</premis:eventDateTime>
                <premis:eventDetailInformation>
                    <premis:eventDetail>program="ClamAV (clamd)"; version="ClamAV 1.2.2"; virusDefinitions="27182/Sun Feb 11 09:33:24 2024"</premis:eventDetail>
                </premis:eventDetailInformation>
                <premis:eventOutcomeInformation>
                    <premis:eventOutcome>Pass</premis:eventOutcome>
                    <premis:eventOutcomeDetail>
                        <premis:eventOutcomeDetailNote></premis:eventOutcomeDetailNote>
                    </premis:eventOutcomeDetail>
                </premis:eventOutcomeInformation>
                <premis:linkingAgentIdentifier>
                    <premis:linkingAgentIdentifierType>preservation system</premis:linkingAgentIdentifierType>
                    <premis:linkingAgentIdentifierValue>Archivematica-1.14.1</premis:linkingAgentIdentifierValue>
                </premis:linkingAgentIdentifier>
                <premis:linkingAgentIdentifier>
                    <premis:linkingAgentIdentifierType>repository code</premis:linkingAgentIdentifierType>
                    <premis:linkingAgentIdentifierValue>wellcome</premis:linkingAgentIdentifierValue>
                </premis:linkingAgentIdentifier>
                <premis:linkingAgentIdentifier>
                    <premis:linkingAgentIdentifierType>Archivematica user pk</premis:linkingAgentIdentifierType>
                    <premis:linkingAgentIdentifierValue>1</premis:linkingAgentIdentifierValue>
                </premis:linkingAgentIdentifier>
            </premis:event>
        </mets:xmlData>
    </mets:mdWrap>
</mets:digiprovMD>
```

### DLIP virus output

Adapting the above Archivematica example, let us assume we want to produce this:


```xml

<mets:mets>
  
  ...

  <mets:amdSec ID="ADM_objects/pxl_20250825_142937791_v17.png">

    <mets:techMD ID="TECH_objects/pxl_20250825_142937791_v17.png">...</mets:techMD>

    <mets:digiprovMD ID="digiprovMD_ClamAV">
        <mets:mdWrap MDTYPE="PREMIS:EVENT">
            <mets:xmlData>
                <premis:event xmlns:premis="http://www.loc.gov/premis/v3" xsi:schemaLocation="http://www.loc.gov/premis/v3 http://www.loc.gov/standards/premis/v3/premis.xsd" version="3.0">
                    <premis:eventType>virus check</premis:eventType>
                    <premis:eventDateTime>2024-03-15T14:34:48.224113+00:00</premis:eventDateTime>
                    <premis:eventDetailInformation>
                        <premis:eventDetail>program="ClamAV (clamd)"; version="ClamAV 1.2.2"; virusDefinitions="27182/Sun Feb 11 09:33:24 2024"</premis:eventDetail>
                    </premis:eventDetailInformation>
                    <premis:eventOutcomeInformation>
                        <premis:eventOutcome>Pass</premis:eventOutcome>
                        <premis:eventOutcomeDetail>
                            <premis:eventOutcomeDetailNote></premis:eventOutcomeDetailNote>
                        </premis:eventOutcomeDetail>
                    </premis:eventOutcomeInformation>
                </premis:event>
            </mets:xmlData>
        </mets:mdWrap>
    </mets:digiprovMD>

  </mets:amdSec>
  
   ... 

</mets:mets>
```

Or in the event of failure:

```xml
    
    ... 

    <premis:eventOutcomeInformation>
        <premis:eventOutcome>Fail</premis:eventOutcome>
        <premis:eventOutcomeDetail>
            <premis:eventOutcomeDetailNote>/home/brian/Test/data/objects/virus_test_file.txt: Eicar-Signature FOUND</premis:eventOutcomeDetailNote>
        </premis:eventOutcomeDetail>
    </premis:eventOutcomeInformation>
```

Working back from this in the METS, we need to be able to PARSE this and turn it into VirusScanMetadata.
This is done in MetsParser as it loops through file elements:

https://github.com/uol-dlip/digital-preservation/blob/cb21241db9f3f36b310d9e31808dc960c6b9b68c/src/DigitalPreservation/Storage.Repository.Common/Mets/MetsParser.cs#L483

I think we'd add a new variable in this loop

```c#
VirusScanMetadata? clamAvMetadata = null; // add this
FileFormatMetadata? premisMetadata = null; // (already there)
```

We'd search for the mets:digiProvMD element and parse it as we do the Premis elements.

And then on line 576 (currently), something like:

```c#
var file = new WorkingFile
{
    ContentType = mimeType ?? ContentTypes.NotIdentified,
    LocalPath = flocat,
    Digest = digest,
    Size = size,
    Name = label ?? parts[^1],
    Metadata = [
        // delete this
        // new VirusScanMetadata
        // {
        //    Source = MetsManager.Mets, 
        //    HasVirus = false
        //},
        new StorageMetadata 
        {
            Source = MetsManager.Mets, 
            OriginalName = originalName, 
            StorageLocation = storageLocation 
        }
    ],
    MetsExtensions = new MetsExtensions
    {
        AdmId = admId,
        PhysDivId = div.Attribute("ID")?.Value,
        AccessCondition = "Open"
    }
};
if (premisMetadata != null)
{
    file.Metadata.Add(premisMetadata);
}
// add this:
if (clamAvMetadata != null)
{
    file.Metadata.Add(clamAvMetadata);
}
mets.Files.Add(file);
```


## Writing AV to METS

The last part is the writing, in `MetsManager`, specifically the `EditMets(..)` method.

This needs a discussion and a walkthrough because currently the AMD SEC that is created or edited here is exactly equivalent to the `FileFormatMetadata` that comes in. (see `PremisManager` for how the child Premis XML block is created or edited).

But the mets:digiProv element that we may or may not need to add or edit is a child element of this. 
So although they come from separate tools and come in as separate, independent `IMetadata` instances, when we write the METS the ClamAV output will get edited *_within_* the premis metadata section.

So this code (which is complex, but well tested) may need some reorganisation, including the potential scenario where there is no Siegfried output but there IS ClamAV output - i.e., there is no incoming `FileFormatMetadata` in the `List<IMetadata> Metadata` property but there is a `VirusScanMetadata`. This is unlikely but would be hard to adapt into the current code.

It's important that this code remains well-tested, it's a critical part of the whole system.



