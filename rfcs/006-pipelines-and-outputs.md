# Pipelines and Outputs

There are two parts to this work, but they are considered together as they overlap.

This RFC describes a process for all tool invocation, but uses the file format identification tool Siegfried as a concrete example, as it is going to be the same approach for all, and Siegfried is the first and most important.

While we could directly use Siegfried's innards (written in Go) and use them selectively, we don't want to do this. We want to treat it as an invocable process, on the command line, that produces an output.

Siegfried has a clear and excellent home page:

https://www.itforarchivists.com/siegfried

In short, it is invoked like this:

```
tomcrane@tomp16s:~/pictures$ sf 372705_001.jpg
---
siegfried   : 1.11.2
scandate    : 2025-04-07T13:39:58+01:00
signature   : default.sig
created     : 2025-03-01T15:28:08+11:00
identifiers :
  - name    : 'pronom'
    details : 'DROID_SignatureFile_V120.xml; container-signature-20240715.xml'
---
filename : '372705_001.jpg'
filesize : 12978775
modified : 2025-02-19T14:13:01Z
errors   :
matches  :
  - ns      : 'pronom'
    id      : 'fmt/43'
    format  : 'JPEG File Interchange Format'
    version : '1.01'
    mime    : 'image/jpeg'
    class   : 'Image (Raster)'
    basis   : 'extension match jpg; byte match at [[0 14] [12978773 2]]'
    warning :
```

But more usually, over a directory, recursive by default, outputting to a file:

```
tomcrane@tomp16s:~$ sf pictures > sf-pictures.yaml
```


The easier part of this work is dealing with the output. Whatever the tool, we want to incorporate the results into the METS file. In the case of Siegfried, this would mean adding elements like this in the technical metadata:

```xml
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

Given the presence of an output YAML file in a Deposit, that refers to files in the Deposit, the Preservation API needs to be able to parse the YAML, extract the file format information, and add it to the METS. The YAML file needs to be in a discoverable location, and the Preservation API needs to know that it is the latest output for the files.


The easiest way for a Siegfried output YAML file to be present in a Deposit is if an archivist has assembled a set of files in a [Bitcurator](https://bitcurator.net/bitcurator/) environment (a VM), run Siegfried on the files in that environment (and probably other tools), then run BagIt to group the files and the tool output(s) into a [BagIt](https://en.wikipedia.org/wiki/BagIt) bag and uploaded the bag to a Deposit working area. In this scenario there is no tool pipeline, the invocation of Siegfried is by a human and the Preservation API is just identifying and incorporating the results from the yaml file.

We already have a pattern for adding files to METS, through the [IMetsManager](https://github.com/uol-dlip/digital-preservation/blob/main/src/DigitalPreservation/DigitalPreservation.Common.Model/Mets/IMetsManager.cs) interface. The implementation here would get more sophisticated as it edits more of the PREMIS metadata section for each file (a fragment of which is above).

> NB Siegfried can output in JSON format by adding the `--json` flag, and while it would be easier for the Preservation API to parse, it isn't the default output format. People would have to remember to do it in BitCurator, and it would be very annoying of you had forgotten. So we should parse YAML first, and we can add a Siegfried JSON output parser later.

> NB Archivists might invoke Siegfried indirectly by running [Brunnehilde](https://www.bitarchivist.net/projects/brunnhilde), which will in turn run Siegfried and other tools including ClamAV. If run this way it will produce a file in CSV format called `siegfried.csv`. **So we need Siegfried parsers for both formats, CSV and YAML**.

However, if the Deposit is not being assembled in BitCurator, then something else needs to run Siegfried over the files.

The most obvious scenarios are:

* Migration of content that doesn't already have its own METS with file format identification (so not EPrints). A script-driven process creates a Deposit, uploads files into the Deposit S3 working area, then asks the Preservation API to add them to the METS file. 
* Manual assembly of a Deposit in the Preservation UI, without first assembling the object in BitCurator
* Subsequent minor edits of an already-preserved Archival Group in the UI

At some point before an ingest job is created, the METS must contain file format identification information. We need to run Siegfried over the files in S3, so that a YAML file exists and then we can invoke the same process as above, something like:

```c#
// in IMetsManager
Task<Result> AddFileFormatInformation(Uri yamlFileLocation, OutputMapping? outputMapping)
```

...where the OutputMapping is an optional property if additional manipulation is required to map the relative paths in the yaml to the relative paths in the Deposit and METS.

So where does Siegfried run?

## ECS For Siegfried with Mounted S3

A containerised service that:

* Has the deposit bucket(s) mounted as a file system ([s3fs](https://github.com/s3fs-fuse/s3fs-fuse) or [mountpoint-s3](https://github.com/awslabs/mountpoint-s3/tree/main))
* Has a background process, that we write in .NET or Python, that listens to SQS
* The background process picks up events from SQS - an instruction to execute a tool over a deposit
* The background process invokes the tool (execute a command line), saving the output *back to the Deposit* at a templated path, something like `/metadata/siegfried/{timestamp}-{some-event-id}/output.yaml` (see discussion of layout later).
* When Siegfried returns (process invocation ends), the background process puts another message on another job-done SQS.
* The Preservation API (likely a new separate process) picks up the "finished" message, which contains the Deposit URI and the tool output location.
* The Preservation API locks the METS file for editing and incorporates the tool output into the METS as above


### Questions (so far)

* It seems these have to be ECS, you can't use s3fs in Fargate
* Do all the tools/pipelines run on the same instance, or does each tool have its own ECS?
* What do we write the background process in? .NET or Python?
* The second "finished" queue could be avoided if the background process updates the Deposit itself (implying .NET for code re-use)
* What if there is an edit conflict? MetsManager uses ETags, but there needs to be a stronger lock while a tool invocation is pending or in process - because it's harder to deal with a conflict.


## Alternative: ECS or Fargate for Siegfried with EBS or EFS

Rather than mount the Deposit directly, the process could begin from the Preservation API with a copy of the Deposit contents onto an EBS volume. The Siegfried ECS/Fargate process can then work on a "real" local file system. The process still needs to put the output back to the S3 bucket.

This might be necessary if for some reason the mounted S3 file system is problematic. Or (more for virus scanning) we might conclude that the s3fs/mountpoint abstraction is going to have to copy/read the whole file anyway, so we might as well do it in one go.


# Comparison with Cambridge approach

This is where the Leeds and Cambridge approaches are probably most similar, as described in [Building our repository ingest workflow](https://digitalpreservation-blog.lib.cam.ac.uk/building-our-repository-ingest-workflow-e09a0d2cdddc). See "How it works".

They scale up the job (Siegfried for file format, ClamAV for virus scanning) from 0 to 1 instances (and possibly beyond) in response to events. There is no evidence of an additional working file system in that diagram.

# Implications for Deposits

Currently all our deposits look like this:

```
(root)/
  --objects/
       (images, docs, more folders etc - the preserved thing)
  --mets.xml
```

However, if you work on files in BitCurator and then bag them, the bag looks like this:

```
(bag)/
   --data/
      (the bagged files)
   --bag-info.txt
   --bagit.txt
   --manifest-sha256.txt
   --tagmanifest-sha256.txt
```

## Proposal - Deposit layout for BagIt

**Firstly**, we make a `metadata/` directory part of our standard template:

```
(root)/
  --metadata/
       (tool outputs etc)
  --objects/
       (images, docs, more folders etc - the preserved thing)
  --mets.xml
```

In this layout, any tool we run via a pipeline can save its output in the `metadata/` folder, in a sub-folder `{toolname}/`, e.g.,

```
(root)/
  --metadata/
     --siegfried/
        --siegfried.yaml
     --clamAV/
        --virusscan.csv
  --objects/
       (images, docs etc - the preserved thing)
  --mets.xml
```

**Secondly**, we support the creation of, and processing of, a Deposit layout that has the above structure one level down. BOTH layouts are supported and the system is clever enough to work out which is being used in any particular Deposit.

So, if you create a new Deposit with a layout "for BagIt" (indicating that you intend to upload a BagIt layout into the Deposit, typically from the BitCurator environment) then you'll get an "empty" layout like this:

```
(root)/
  --data/
     --metadata/
     --objects/
     --mets.xml
```

You then upload your bag _into_ this structure - it should match, so you basically fill the structure. Your upload should not include a METS file, but will include, in metadata, any tool outputs you have run.

An example flow might be starting with the raw data here:
https://github.com/uol-dlip/digital-preservation-e2e-tests/tree/bitcurator-fixtures/test-data/bitcurator/original/tom-example-1

![Original analysed layout](img/original-layout.png)

In the BitCurator environment, you run Brunnehilde on this data:

```
> brunnhilde.py --hash sha256 /home/test-data/bitcurator/tom-example-1 analysis-of-tom-1
```

This saves the Brunnehilde output in `tom-example-1/` in the home directory (in the absence of a fuller path):

![Brunnehilde output](img/brunnehilde-output.png)

> _The exact workflow in BitCurator is up to the archivist, this is just an example. It's the final layout for bagging that's important. But note that this workflow also generates a virus scan report._


What we want to do now is produce a layout with our files for preservation in `objects/` and the tool output(s) in `metadata/`, in sub folders named for their tools. So, we arrange our working files like so:

![Ready for bagging](img/ready-for-bagging.png)


> _We captured sha256 when we ran Brunnehilde or Siegfried directly. We are going to capture sha256 again when we run BagIt, so even the unlikely event of corruption while assembling the files for bagging will be detectable later; the Preservation API will match the captured hashes from both sources._


This is now ready for bagging. If the above image shows the contents of the directory `tom-example-1/`, then we run bagit on that directory. At its simplest with "bag in place" behaviour:

```
> bagit.py --source-organization DLIP --sha256 tom-example-1
```

...this produces the layout:

![Bagged object](img/bagged.png)

We need a Deposit to upload this into. In the UI, we can create one either from scratch, or by entering an EMu CATIRN or Identity Service PID:

_(screen shot if and when implemented!)_

We tick the box "This Deposit will be populated with a BagIt bag", and a deposit with the "empty" layout is created:

```
(root)/
  --data/
     --metadata/
     --objects/
     --mets.xml
```

Using our transfer tool of choice, we then upload the created Bag contents into this structure.

> At time of writing the only tool that will do this is the AWS Console, which Archivists will need access to until another transfer mechanism is possible. Note that the Preservation UI allows you to open the AWS Console _directly_ at the right location for upload - as long as you have permission to see it.

Care must be taken to match the directory structure so, that we end up with the Deposit looking like this:

```
(root)/
   --data/
     --metadata/
        --brunnehilde/
           --csv_reports/
              --formats.csv
              --formatVersions.csv
              --mimetypes.csv
              --years.csv              
           --logs/
              --viruscheck-log.txt
           report.html
           siegfried.csv
           tree.txt           
     --objects/
        --awkward/
           --7 ways to celebrate #WomensHistoryMonth 💜 And a sneak peek at SICK new art.htm
           --慷獹琠散敬牢瑡圣浯湥䡳獩潴祲潍瑮㼿䄠摮愠猠敮歡瀠敥瑡匠䍉敮⁷牡�.msg
        --nyc/
           --DSCF0969.JPG
           --(...11 more files...)
        --372705_001.jpg
        --Fedora-Usage-Principles.docx
        --IMAGE-2.tiff
        --warteck.jpg        
     --mets.xml
   --bag-info.txt
   --bagit.txt
   --manifest-sha256.txt
   --tagmanifest-sha256.txt
```

At this point the `mets.xml` file is still the one created when the Deposit was created - it doesn't have anything about the new files in it yet - the Preservation API is unaware of what you have been up to in S3.

In the Deposit UI, the METS can be updated in two steps (could be one, but maybe stick with two for safety/explicitness):

![Add to METS](img/add-to-mets.png)

> _All the operations can be done via the API directly (and therefore scripted) as well as the Web user interface._

This process finds and reads ALL tool outputs it recognises (Siegfried initially) and incorporates the information into the METS file.


## Deposit behaviour

A BagIt-based deposit is the same as a normal deposit, it just has the relevant files and folders one level down under `data/` rather than in the root. And we now treat `metadata/` as part of the normal template.

If you run an import job, the created Archival Group **does not have this additional data directory** - it has `objects/`, `metadata/` and `mets.xml` at the root. And if you then export the Archival Group into a new Deposit (for example, to create a v2) it exports with `objects/`, `metadata/` and `mets.xml` at the root: no `data/` directory.

During this process the bagit .txt files in the root are copied into a `__bagit/` directory in `metadata/` (note the two underscores) for future reference.


> The role of BitCurator and BagIt in **editing** an Archival Group once preserved - in subsequent versions - is not defined; we need to work on that in Phase 2. The above discussion would allow edits via the API and UI, but what about going back to BitCurator and re-bagging? _That_ workflow is not defined.


## Tools / pipeline revisited

In the above discussion no tool/pipeline invocation happened because the tools were run in the BitCurator environment.

The outputs were manually put into the deposit (in appropriate locations under `metadata/`) and then the Preservation API processed them.

This latter processing step is identical in a pipeline operation, and the layout of the deposit is identical, except that the production of the tool outputs is automated - given a Deposit, a pipeline running on that deposit will run the same tools used by the archivist in the BitCurator environment and save the outputs in the same way, and then invoke the integration with METS. The mechanism used to run the tool(s) on the files in the Deposit S3 location is independent of the rest of this flow, it just needs to accept the same starting conditions and deliver the same ending conditions.


## Tool outputs from pipelines

Again - what about pipelines being run on Deposits that are already BagIt-based? This should work fine; the initial metadata was used to populate METS, subsequent runs might update or replace the metadata.

Should pipeline runs put their outputs into timestamped folders under `metadata/`? 

```
...
   metadata/
      pipelines/
         2025-04-21T12:00:00/
            siegfried/
               --etc
```

In this scenario the tool-output-processing code is just extended to find the _latest_ outputs, allowing for multiple runs.


## Workflow

Initial:

```
working-dir/
   --my-item/
      --metadata/
         -- (initially empty)
      --objects/
         -- (here are the actual files and folders of the thing)
```

Run command:

```
user@BitCurator:~/working_dir$ brunnhilde.py --hash sha256 my-item/objects my-item/metadata/brunnhilde
```

(i.e., run Brunnhilde over the objects directory inside my-item, and save the output in a brunnhilde folder inside the metadata folder inside my-item)

This produces:

```
working-dir/
   --my-item/
      --metadata/
         --brunnhilde/
            --csv_reports/
               --formats.csv
               --formatVersions.csv
               --mimetypes.csv
               --years.csv
            --logs/
               --viruscheck-log.txt
            --report.html
            --siegfried.csv
            --tree.txt
      --objects/
         -- (here are the actual files and folders of the thing)
```

You could also do just Siegfried, or even both. For example, if we now did:

```
user@BitCurator:~/working_dir$ mkdir my-item/metadata/siegfried
user@BitCurator:~/working_dir$ sf -hash sha256 my-item/objects > my-item/metadata/siegfried/siegfried.yml
```

... then we'd end up with an additional `siegfried` folder:


```
working-dir/
   --my-item/
      --metadata/
         --brunnhilde/
            --csv_reports/
               --formats.csv
               --formatVersions.csv
               --mimetypes.csv
               --years.csv
            --logs/
               --viruscheck-log.txt
            --report.html
            --siegfried.csv
            --tree.txt
         --siegfried/
            --siegfried.yml
      --objects/
         -- (here are the actual files and folders of the thing)
```

Again the actual files are untouched, we have been running tools from outside `my-item/`, on the `objects/` folder _inside_ `my-item/`, and saving the outputs inside a "tool-name" directory inside the `metadata/` folder in `my-item/`.

Now we can bag this:

```
user@BitCurator:~/working_dir$ bagit.py --source-organization uol-dlip --sha256 my-item
```

This is a "bag in place" and it moves the contents of `my-item/` one level down:

```
working-dir/
   --my-item/
      --data/
         --metadata/
            --brunnhilde/
               -- (as above, omitted for brevity)
            --siegfried/
               --siegfried.yml
         --objects/
            -- (here are the actual files and folders of the thing)
      --bag-info.txt
      --bagit.txt
      --manifest-sha256.txt
      --tagmanifest-sha256.txt
```

The content of my-item is what we upload into the deposit - i.e., data/ and the bagit files end up in the root of the deposit.



## Notes

Format expected from BitCurator

```
\-- (bagged-folder)
    \-- data
        \-- objects
            (the files to be preserved)
        \-- metadata
            (tool-outputs from siegfried et el)
     -- manifest-sha256.txt
     -- bagit.txt
```
