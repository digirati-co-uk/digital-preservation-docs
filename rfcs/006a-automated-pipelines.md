# Automated Pipelines

This RFC continues on from [RFC 006](006-pipelines-and-outputs.md). In that we finish up with a working human-driven process:

 - User works on files in BitCurator environment in standard layout with `objects/` and `metadata/` folders; the actual content is in `objects/`, and `metadata/` is initially empty.
 - User runs tools (e.g., Brunnehilde or Siegfried) that produce output in the `metadata/` folder (see [Workflow](006-pipelines-and-outputs.md#workflow)).
 - User runs BagIt to produce a BagIt layout
 - In the Preservation UI, user creates a Deposit with BagIt layout (they can do this at any step before this one, too)
 - Looking at the Deposit Page in a browser running _in the BitCurator VM_ they click Actions -> Open Deposit Location. This opens a new tab with the S3 Console at the right place.
 - They upload the BagIt layout over the top of the deposit - not replacing the METS but filling the objects and metadata folders.
 - In the Preservation UI they then click Actions -> Refresh storage (The Preservation UI doesn't know what they were doing!)
 - This will tell them that they have a load of files not in the METS
 - Actions -> Select all non-METS
 - Actions -> Add selected to METS
 - Now that information gathered by the tools in BitCurator is present in the METS, in the administrative metadata sections. 
 - It is now possible to create an import job, because every file has a checksum in METS.

There is a video of this process, see here: (TBC)

We need to _automate_ this process. The above will always need supporting, but we also want to be able to support the following flow:


 - In the Preservation UI, user creates a Deposit (in either layout)
 - User adds files to `objects/` folder - either by uploading from the UI, or behind the scenes directly to the AWS Deposit location
 - (optional) User clicks Actions -> Refresh storage (this is likely, they'll want to check what they added if they did it behind the scenes)
 - NEW User clicks Actions -> Run pipelines

 This is now the automated pipeline:

 - The Preservation API locks the Deposit as pipeline user
 - ??? (some asynchronous queue-based job)
 - The metadata folder is now populated with tool outputs
 - The Preservation API refreshes the storage
 - The Preservation API unlocks the deposit
 - The user can decide whether to add to METS at this stage (or maybe this happens automatically)

 This RFC explores the ??? above. There are already some notes about possible approaches in [RFC 006](006-pipelines-and-outputs.md#ecs-for-siegfried-with-mounted-s3) and [RFC 006](006-pipelines-and-outputs.md#alternative-ecs-or-fargate-for-siegfried-with-ebs-or-efs). This RFC decides on the approach we're going to take.

 
Initially, it will be OK to just run Brunnhilde, because that will run Siegfried and ClamAV for us.

Later on we can add more tools.

 ## Existing features of Preservation API

 The contents of a Deposit are managed by the [WorkspaceManager](https://github.com/uol-dlip/digital-preservation/blob/main/src/DigitalPreservation/DigitalPreservation.Workspace/WorkspaceManager.cs) class. This is used by the Preservation API when you invoke operations on it, but it is also used directly by the UI - the Preservation API doesn't have to see everything you are up to behind the scenes.

 The task the automated pipeline has to do doesn't really touch this though, all it needs to do is ensure the contents of `objects/` are inspected by tools, and the tool outputs are placed in known locations under `metadata/`. This is more a FYI - how when you refresh storage, ahead of adding files to METS, the WorkspaceManager (indirectly via various Mediatr calls) uses a [MetadataReader](https://github.com/uol-dlip/digital-preservation/blob/main/src/DigitalPreservation/DigitalPreservation.Workspace/MetadataReader.cs) object to extract the information it needs from the tool output files.



