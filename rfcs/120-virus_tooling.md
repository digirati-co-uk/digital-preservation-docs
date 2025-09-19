# Virus scanning and dealing with outputs

We will use ClamAV to scan deposit files for viruses as part of the pipeline.

We can either run it on its own, or via Brunnhilde. Seeing as we are already doing the latter this may be the simplest way.

The Freshclam tool should be run at least at the start of each day to update the virus definition files:

https://docs.clamav.net/manual/Usage/SignatureManagement.html

BClamAV will still run without this but will emit warnings when its definition files are more than 7 days old.

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

This class isn't doing much at the moment but is used in the UI. Tha actual fields of this class are ultimately dependent on:

 - what info is available
 - what we want to surface in the UI
 - what we want to write to the METS.


 








