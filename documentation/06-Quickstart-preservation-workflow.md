# Preservation Workflow for external applications

This document is for consumers of the Preservation API who *manage and supply their own METS file*.

Such consumers will create Deposits, Create and run import jobs, browse the repository, retrieve Archival Groups and export Archival Groups into new Deposits from which new versions can be created.

Such consumers do not use the API to manage or edit the METS file itself, run analysis tools or other operations. Such consumers are using the Preservation API for versioned object storage, rather than for generating or managing the content of those objects.

## Making a Container

Use case: you want to store new objects under a particular Container in the repository tree, but the Container doesn't exist yet.

> [!IMPORTANT]
> This is only for creating repository structure _outside_ of preserved digital objects; you cannot create Containers within preserved objects via the API, only by importing deposits.

## Preserve a digital object for the first time

Use case: Preserve a Digital Object (a set of files that includes a METS file describing the object)
The object does not yet exist in the repository, this will be version "v1"

1. Create a Deposit
2. Upload the files of the object to the location provided by the Deposit's `files` property
3. Set the Deposit's Archival Group `id` (where in the repository you want to store the object) and the Archival Group `name`
4. Create and execute an Import Job in a single operation
5. Poll the returned ImportJobResult until its status is "complete"

> [!TIP]
> Step 3 can be combined with step 21

## Loading an Archival Group

1. Make a GET request for the Archival Group `id`

## Creating a Deposit from an identifier

This is where the API recognises your supplied identifier (typically a catalogue identifier of some sort) and creates a Deposit for you with the correct Archival Group URI, Archival Group Name and template.

This is the same as the above example except that you don't need step 3.

## Preserve a new version of a digital object - full export

> [!IMPORTANT]
> This does a full export to S3 of the Archival Object, making copies of the Containers and Binaries in the Deposit working space (the location given by its `files` property).

Use case: you need to view or work with the complete set of files of the Archival Group in order to make changes for a new version.

1. Create an export job - which creates a Deposit and copies the files of the object to the location provided by the Deposit's `files` property
2. Poll the returned export job until its status is "new" - the files have finished being copied
3. Modify the files as needed - adding, deleting, patching, renaming
4. Create and execute an Import Job in a single operation
5. Poll the returned ImportJobResult until its status is "complete"

## Preserve a new version of a digital object - no export

1. Create a Deposit 
2. Poll the returned export job until its status is "new" - the files have finished being copied
3. Modify the files as needed - adding, deleting, patching, renaming
4. Create and execute an Import Job in a single operation
5. Poll the returned ImportJobResult until its status is "complete"


## Preserve a new version of a digital object - custom patch





