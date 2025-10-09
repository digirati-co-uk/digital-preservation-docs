# Preservation Workflow for external applications

This document is for consumers of the Preservation API who *manage and supply their own METS file*.

Such consumers will create Deposits, Create and run import jobs, browse the repository, retrieve Archival Groups and export Archival Groups into new Deposits from which new versions can be created.

Such consumers do not use the API to manage or edit the METS file itself, run analysis tools or other operations. Such consumers are using the Preservation API for versioned object storage, rather than for generating or managing the content of those objects.

## Making a Container

Use case: you want to store new objects under a particular Container in the repository tree, but the Container doesn't exist yet.

> [!IMPORTANT]
> This is only for creating repository structure _outside_ of preserved digital objects; you cannot create Containers within preserved objects via the API, only by importing deposits.

```
GET /repository/library/c20-printed-books
=> 404 Not Found

GET /repository/library
=> 200 OK (returns Container object)

PUT /repository/library/c20-printed-books
{
  "type": "Container",
  "name": "20th Century Printed Books"
}
=> 201 Created
```



## Preserve a digital object for the first time

Use case: Preserve a Digital Object (a set of files that includes a METS file describing the object)
The object does not yet exist in the repository, this will be version "v1"

1. Create a Deposit
2. Upload the files of the object to the location provided by the Deposit's `files` property
3. Set the Deposit's Archival Group `id` (where in the repository you want to store the object) and the Archival Group `name`
4. Create and execute an Import Job in a single operation
5. Poll the returned ImportJobResult until its status is "complete"

> [!TIP]
> Step 3 can be combined with step 1

### 1. Create a Deposit

```
POST /deposits
{
}
```

Minimally an empty object is OK, though unusual. You might want to provide more details up front:

```
POST /deposits
{
    type: "Deposit",
    archivalGroup: "https://preservation.api/repository/library/c20-printed-books/my-book",
    archivalGroupName: "My Book",
    submissionText: "A note from me for anyone interested"
}
```

This will return HTTP 201, with the new Deposit as the response body:

```json
{
  "id": "https://preservation.api/deposits/szwettbzp4xw",
  "type": "Deposit",
  "archivalGroup": "https://preservation.api/repository/library/c20-printed-books/my-book",
  "archivalGroupExists": false,
  "files": "s3://your-working-bucket/deposits/szwettbzp4xw/",
  "status": "new",
  "submissionText": "A note from me for anyone interested",
  "archivalGroupName": "My Book",
  "active": true,
  "preserved": null,
  "preservedBy": null,
  "versionPreserved": null,
  "exported": null,
  "exportedBy": null,
  "versionExported": null,
  "created": "2025-10-02T15:30:51.631328Z",
  "createdBy": "https://preservation.api/agents/tom",
  "lastModified": "2025-10-02T15:30:51.631328Z",
  "lastModifiedBy": "https://preservation.api/agents/tom",
  "metsETag": "\"a29a88372f20681b6d1877e3ca93fae1\"",
  "lockedBy": null,
  "lockDate": null
}
```

### 2. Upload files

The above newly created Deposit has a `files` property of "s3://your-working-bucket/deposits/szwettbzp4xw/". This is where you put the content of the new object, interacting directly with (in this case) the AWS API or (if a file share) other file copying mechanisms.

The files should include a METS file that provides SHA256 digests for each file in a `premis` object under the file's AMDSec element.

> [!TIP]
> If uploading files to S3, set the optional `ChecksumAlgorithm` of the `PutObjectCommand` to "SHA256". AWS will calculate a SHA256 checksum and store it in the object's S3 metadata. It is not _required_ to do this if SHA256 digests are provided by a METS file, but it both are present, the API will verify that they match.


### 3. Set additional Deposit properties

If the Deposit was created from an empty object, or if you want to change any of the details, you can patch any of the fields `archivalGroup`, `archivalGroupName` and `submissionText`:

```
PATCH /deposits/szwettbzp4xw
{
  "archivalGroup": "https://preservation.api/repository/library/c20-printed-books/my-other-book",
  "submissionText": "I changed my mind about what this is called",
  "archivalGroupName": "My Other Book"
}
```

### 4. Create and execute an Import Job in a single operation

This is a shortcut when you don't need to see or modify the import job and can rely on the API to generate it for you.

```
POST /deposits/szwettbzp4xw/importjobs
{
  "id": "/deposits/szwettbzp4xw/importjobs/diff"
}
```

> [!TIP]
> This is equivalent to `GET /deposits/szwettbzp4xw/importjobs/diff` and then `POST /deposits/szwettbzp4xw/importjobs` with the returned body.

The returned object is an `ImportJobResult`:

```json
{
    "id": "https://preservation.api/deposits/szwettbzp4xw/importjobs/results/ge7n4ds2",
    "type": "ImportJobResult",
    "importJob": "https://preservation.api/deposits/szwettbzp4xw/importjobs/ge7n4ds2",
    "originalImportJobId": "https://preservation.api/deposits/szwettbzp4xw/importjobs/diff",
    "deposit": "https://preservation.api/deposits/szwettbzp4xw",
    "ArchivalGroup": "https://preservation.api/repository/library/c20-printed-books/my-other-book",
    "status": "waiting",
    "dateBegun": null,
    "dateFinished": null,
    "newVersion": null,
    "errors": [],
    "containersAdded": [],
    "binariesAdded": [],
    "containersDeleted": [],
    "binariesDeleted": [],
    "binariesPatched": []
}
```

### 5. Poll the returned ImportJobResult until its status is "complete"

You can do this as little or often as you like (or even not at all):

```
GET /deposits/szwettbzp4xw/importjobs/results/ge7n4ds2
```

Returns the same ImportJobResult as above, but over time we expect to see the `status` change to "complete" and the `binariesAdded`, etc., populated.


## Loading an Archival Group

Whether it's one you have just created, or one that has existed for a long time, this is no different from browsing any other structural Container or Archival Group in the API:

```
GET /repository/library/c20-printed-books/my-other-book
```

This returns the full Archival Group.

> [!TIP]
> When you request Containers above or below the level of an Archival Group, only their immediate child members (`containers` and `binaries`) are populated. However, when you request an Archival Group (which is also a type of Container) the full hierarchy is populated - all descendant Containers and Binaries, no matter how deep. An Archival Group is a complete representation of the preserved object in the repository.

## Creating a Deposit from an external identifier

This is where the API recognises your supplied identifier (typically a catalogue identifier of some sort) and creates a Deposit for you with the correct Archival Group URI, Archival Group Name and template.

This is the same as the initial example except that you don't need step 3 - you don't need to supply the intended archivalGroup URI, or a title.

```
POST /deposits/from-identifier
{
    "schema": "catirn",
    "value": "1000001"
}
```

This will return HTTP 201, with the new Deposit as the response body:

```jsonc
{
  "id": "https://preservation.api/deposits/de45pa992ssf",
  "type": "Deposit",
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001",
  "archivalGroupName": "A Treatise on Opticks",
  "files": "s3://your-working-bucket/deposits/de45pa992ssf/",
  "archivalGroupExists": false,
  "status": "new",
  // other fields similar to first example
}
```

In this example the API consulted an external service to learn that "1000001" should be preserved at .../library/c18-printed-books/a-10000001 and that its title is "A Treatise on Opticks".

The possible values of `schema` depend on the configuration of the API and what system(s) it is integrated with.

From this point on the flow is the same as the first Deposit example.


## Preserve a new version of a digital object - full export

> [!IMPORTANT]
> This does a full export to S3 of the Archival Object, making copies of the Containers and Binaries in the Deposit working space (the location given by its `files` property).

Use case: you need to view or work with the complete set of files of the Archival Group in order to make changes for a new version.

1. Create an export job - which creates a Deposit and copies the files of the object to the location provided by the Deposit's `files` property
2. Poll the returned export job until its status is "new" - the files have finished being copied
3. Modify the files as needed - adding, deleting, patching, renaming
4. Create and execute an Import Job in a single operation
5. Poll the returned ImportJobResult until its status is "complete"


## 1. Create an export job

The intention is to create a Deposit that has all the files of an existing Archival Group. In the same way that you POST a partial Deposit in the earlier example, you POST a deposit to the export endpoint with at least the `archivalGroup` property:

```
POST /deposits/export
{
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001"
}
```

If you wish to export a specific version of an Archival Group:

```
POST /deposits/export
{
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001",
  "versionExported": "v7"
}
```

Usually `versionExported` is not set on the POST and the **latest** version is exported. This will always be returned on the Deposit from the API:

```jsonc
{
  "id": "https://preservation.api/deposits/fcc44m9b8a",
  "type": "Deposit",
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001",
  "archivalGroupName": "A Treatise on Opticks",
  "files": "s3://your-working-bucket/deposits/fcc44m9b8a/",
  "archivalGroupExists": true,
  "status": "exporting",
  "versionExported": "v1",
  // other fields similar to first example
}
```

## 2. Wait for export to finish

The `status` of the immediately returned Deposit will be "exporting". You can't start working with the Deposit until this status becomes "new".

```
GET /deposits/fcc44m9b8a
```

```jsonc
{
  "id": "https://preservation.api/deposits/fcc44m9b8a",
  // (fields omitted)
  "status": "new",
  // (fields omitted)
}
```

## 3. Modify the files as needed

From here the flow is the same as the original example - typically upload files to S3, and/or remove files from S3, and update the METS file to reflect the changed object.

## 4. Create and execute an Import Job in a single operation

As in step 4 in the original example. A new `ImportJobResult` is returned.

## 5. Poll the returned ImportJobResult until its status is "complete"

As in step 5 of the original example.

While the job is processing, the `sourceVersion` will show what version of the Archival Group the import is based on:

```jsonc
{
    "id": "https://preservation.api/deposits/fcc44m9b8a/importjobs/results/km7b992sd",
    "type": "ImportJobResult",
    // 
    "status": "running",
    "sourceVersion": "v1",
    //
}
```

When completed, the new version is available on the ImportJobResult:

```jsonc
{
    "id": "https://preservation.api/deposits/fcc44m9b8a/importjobs/results/km7b992sd",
    "type": "ImportJobResult",
    // 
    "status": "completed",
    "sourceVersion": "v1",
    "newVersion": "v2",
    //
}
```

## Preserve a new version of a digital object - no export

This is very similar to the export example.

1. Create a Deposit 
2. Poll the returned export job until its status is "new" - the files have finished being copied
3. Modify the files as needed - adding, deleting, patching, renaming
4. Create and execute an Import Job in a single operation
5. Poll the returned ImportJobResult until its status is "complete"

The difference is that in step 1, you POST the partial Deposit to the /deposits endpoint rather than /deposits/export:

```
POST /deposits/export
{
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001"
}
```

This **_still exports the METS file_** but no other files.

From then on the flow is the same.

In Step 3, if (for example) you added a single file, and modified the METS file to include that new file, then because the API can read the METS file it will produce an Import Job with one Binary to add (your new file) and one Binary to patch (the METS file). 

If instead of Step 4 you first create the import job:

```
GET /deposits/bb7c8mast5/importjobs/diff
```

... you can inspect it to verify that it's actually what you want to happen:

```jsonc
{
  "id": "https://preservation.api/deposits/bb7c8mast5/importjobs/transient/638950821343621834",
  "type": "ImportJob",
  "originalId": "https://preservation.api/deposits/bb7c8mast5/importjobs/diff",
  "deposit": "https://preservation.api/deposits/bb7c8mast5",
  "created": "2025-10-03T09:55:34.3621834Z",
  "createdBy": "https://preservation.api/agents/tom",
  "lastModified": "2025-10-03T09:55:34.3621834Z",
  "lastModifiedBy": "https://preservation.api/agents/tom",
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001",
  "archivalGroupName": "Import job for Documentation",
  "isUpdate": true,
  "source": "s3://your-working-bucket/deposits/bb7c8mast5/",
  "sourceVersion": "v2",
  "ContainersToAdd": [],
  "BinariesToAdd": [
    {
      "id": "https://preservation.api/repository/library/c18-printed-books/a-10000001/objects/my-new-file.png",
      "type": "Binary",
      "name": "my-new-file.png",
      "origin": "s3://your-working-bucket/deposits/bb7c8mast5/objects/my-new-file.png",
      "contentType": "image/png",
      "size": 449518,
      "digest": "1587a18ce3567215bfba9d0866b9e05e548b0ba70ab1b6e001a96a2f0e95c7f3"
    }
  ],
  "ContainersToDelete": [],
  "BinariesToDelete": [],
  "BinariesToPatch": [
    {
      "id": "https://preservation.api/repository/library/c18-printed-books/a-10000001/mets.xml",
      "type": "Binary",
      "name": "mets.xml",
      "origin": "s3://your-working-bucket/deposits/bb7c8mast5/mets.xml",
      "contentType": "application/xml",
      "size": 3278,
      "digest": "2274bfad9b5420043fc62c6c34441ae436a0caab12d8a62a4679f4dfb2599e53"
    }
  ],
  "ContainersToRename": [],
  "BinariesToRename": []
}
```

You can then POST this object to the /importjobs endpoint for the Deposit:

```
POST /deposits/bb7c8mast5/importjobs
{
  "id": "https://preservation.api/deposits/bb7c8mast5/importjobs/transient/638950821343621834",
  "type": "ImportJob",
  // (the rest of the fields in the object above)
}
```

## Preserve a new version of a digital object - custom patch

You don't have to use an ImportJob generated by the platform as a diff.

You must always create a Deposit from which to run the job, but you can manually construct the ImportJob, giving it any `id` you like.

The `id` properties of the Containers and Binaries listed must belong to the target Archival Group (even if they don't exist yet they must be under the path), but the `origin` from which the Binary is copied doesn't have to be the same relative path as its target under the Archival Group. For example, you might want to patch page 637 of a 1000-page manuscript without worrying about aligning the paths:

```jsonc
{
  "id": "https://example.org/my-custom-unique-uri-for-this-job",
  "type": "ImportJob",
  "deposit": "https://preservation.api/deposits/hn66d3s9b",
  "archivalGroup": "https://preservation.api/repository/library/c18-printed-books/a-10000001",
  "isUpdate": true,
  "source": "s3://your-working-bucket/deposits/hn66d3s9b/",
  "sourceVersion": "v3",
  "BinariesToAdd": [
    {
      "id": "https://preservation.api/repository/library/c18-printed-books/a-10000001/objects/some/detailed/path/page-637.tiff",
      "type": "Binary",
      "name": "page-637.tiff",
      "origin": "s3://your-working-bucket/deposits/hn66d3s9b/patch-of-p637.tif",
      "contentType": "image/tiff",
      "size": 4439518,
      "digest": "ca20043fc62c7215bfba9d0866b9e0e548b0ba70ab1b6e001a96d8a62a469f4d"
    }
  ],
  "BinariesToPatch": [
    {
      "id": "https://preservation.api/repository/library/c18-printed-books/a-10000001/mets.xml",
      "type": "Binary",
      "name": "mets.xml",
      "origin": "s3://your-working-bucket/deposits/hn66d3s9b/mets.xml",
      "contentType": "application/xml",
      "size": 3278,
      "digest": "2274bfad9b5420043fc62c6c34441ae436a0caab12d8a62a4679f4dfb2599e53"
    }
  ]
}
```

Here we have a file `patch-of-p637.tif` that will become the Binary in the Archival Group `https://preservation.api/repository/library/c18-printed-books/a-10000001/objects/some/detailed/path/page-637.tiff`. There was no need to ask for a diff, the API client can construct and submit this job directly.


