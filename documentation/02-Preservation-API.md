# Preservation API

Throughout this document we will assume for examples that the Preservation API root is at https://preservation-api.library.leeds.ac.uk. There is no API functionality at this root URI, however. The API is JSON over HTTP; most resources have `id` properties that correspond to their HTTP locations, and refer to other resources via fully qualified URIs.

The Preservation API is consumed by the applications we build to implement Preservation tasks:

 - The **Preservation UI** at preservation.library.leeds.ac.uk. This uses the API described here to offer a user interface over the preservation functionality.
 - **iiif-builder**. This Python process reads an _activity stream_ provided by Preservation API to find new preserved objects to process, then makes further calls to the Preservation API to obtain information about the objects (specifically an _Archival Group_ and its _METS file_).
 - **Goobi** uses the Preservation API to store digitised objects coming through its workflow, and retrieve them for later work if necessary.
 - Other ad hoc scripts and tools that will be written over time.

Whereas the [Storage API](03-Storage-API.md) is a wrapper around Fedora that bridges files-to-be-preserved to Fedora [Archival Groups](https://wiki.lyrasis.org/display/FEDORA6x/Glossary#Glossary-ArchivalGroupag), so the Preservation API bridges Leeds business rules, models of Archival Groups and born digital workflow to the Storage API. These processes are then doubly insulated against the specifics of Fedora.

For example:

- The Storage API doesn't know what a [METS file](https://www.loc.gov/standards/mets/) is, it's just another file being preserved as part of an _ArchivalGroup_.
- The Preservation API *does* know what a METS file is, and may use its contents (e.g., checksums, original file names) to construct calls to the Storage API.

However, there are concepts that are common to both, where the Preservation API is basically passing information from or to the Storage API. An example of this is browsing the repository via the API, which passes through (in simplified form) the Storage API concepts of Containers and Binaries.

This documentation deals with the Preservation API working on content in Amazon AWS S3, rather than on local file systems or other cloud storage providers. However, it can work with these other sources; examples are limited to S3 for brevity. The Preservation API assumes that its callers have access to one or more AWS S3 working bucket(s), that they can place content into, or in the case of exports, fetch content from.


## Authentication

> [!WARNING]
> TODO - Leeds MSAL specifics

The API implements a standard OAuth2 [Client Credentials Flow](https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/) for machine-to-machine access, with [Refresh Tokens](https://www.oauth.com/oauth2-servers/access-tokens/refreshing-access-tokens/) to ensure that access tokens are short lived and can be revoked.


## Resource Types

The resources sent to the API and retrieved from the API over HTTP are JSON objects. These are the core types:

 - **ArchivalGroup**: a preserved _thing_ or object, a set of files in the underlying Fedora repository. It may be just one file, or may be thousands with a complex internal directory structure. ArchivalGroups created by the Preservation API include a METS file that describes the object and provides technical, structural and administrative metadata. An ArchivalGroup returned by the Preservation API corresponds to a [Fedora Archival Group](https://wiki.lyrasis.org/display/FEDORA6x/Glossary#Glossary-ArchivalGroupag), which in turn corresponds to an [OCFL object](https://ocfl.io/1.1/spec/#object-spec) in the Fedora S3 bucket.
 - **Container**: represents a directory or folder in the repository - both for folders within an ArchivalGroup, and for organisational structure in the repository above the level of an ArchivalGroup.
 - **Binary**: any file - text, images, datasets etc. Can only exist within an ArchivalGroup.
 - **Deposit**: a working set of files intended for Preservation (intended to become an ArchivalGroup) and also used for later updates to an ArchivalGroup after an export. Either way, the Deposit provides a "working area" outside of the repository that you can put files in, or collect them from in the case of an export. 
 - **ImportJob**: a set of instructions to the Preservation API to create or modify an ArchivalGroup - the Containers and Binaries from a Deposit to preserve. For some workflows you might edit this manually but for others you might never need to see it, the API will create it for you my comparing the deposit working files to the preserved Archival Group; the import job is then the actions required to synchronise the two.
 - **ImportJobResult**: a report on the execution of an ImportJob. It can be used to track an ongoing job as it is running, or for later examination.
 - **Export**: represents the result of asking the API to export the contents of an ArchivalGroup into a Deposit's working area. Callers can use this resource to determine when the export has finished (an export may take a long time) and to see a list of files exported.

Additional resource types for working with METS files, tool outputs and managing the contents of a Deposit are introduced in context.


### Common metadata

The resource types above all share a set of common properties:

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/...(path)...",
    "type": "(Resource)", // One of those above
    "created": "2024-03-14T14:58:46.102335Z", 
    "createdBy": "https://preservation-api.library.leeds.ac.uk/users/tom",
    "lastModified": "2024-03-28T12:00:00.00000Z",
    "lastModifiedBy": "https://preservation-api.library.leeds.ac.uk/users/donald",
    // ...
    // Other type-specific properties
    // ...
}
```

| Property         | Description                       | 
| ---------------- | --------------------------------- |
| `id`             | URI of the resource in the API. The path may only contain characters from the *permitted set*.   |
| `type`           | The type of the resource |
| `created`        | ISO 6801 DateTime string representing the creation date of the resource within the Preservation system (not its original external creation date). |
| `createdBy`      | A URI representing the user who created this resource (may be an API user) | 
| `lastModified`   | ISO 6801 DateTime string representing the last modified date of the resource within the Preservation system (not its original external last modified date). |
| `lastModifiedBy` | A URI representing the user who last modified this resource (may be an API user) |      



The *permitted set* of characters that may be used in resource ids (URIs) are the lower case letters `a-z`, upper case letters `A-Z`, the numbers `0-9`, and the characters `(`, `)`, `-`, `_`, and `.` with `%` allowed in escape sequences. Resources that represent preserved or to-be-preserved files and folders have a `name` property that can take any UTF-8 characters; this property is used to record the original name of the resource, typically to preserve exact file names that would be fragile or ugly in escaped URLs.

The resource types `ImportJob` and `ImportJobResult` also have the first four of these properties, but not `lastModified` and `lastModifiedBy` (as they cannot be modified).


### 📁 Container

For building structure to organise the repository into a hierarchical layout. Containers also represent directories within an ArchivalGroup.

 - Only some API users can create Containers within the repository. Other users are given an existing Container, or set of Containers, that they can create ArchivalGroups in.
 - Containers are also used to represent directories within an ArchivalGroup, but no user of the API can create them inside an ArchivalGroup directly. Instead they are created indirectly as part of an ImportJob - the ImportJob specifies `containersToAdd` (see below).

A Container retrieved while browsing the repository via the API might look like this:

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1/my-directory",
    "type": "Container",
    "name": "my-dírèçtóry",    // carries the original name of the directory
    "containers": [],
    "binaries": [
        // ... see below  
    ],
    "partOf": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1"
}
```

| Property     | Description                       | 
| ------------ | --------------------------------- |
| `id`         | URI of the Container in the API. The path part of this URI may only contain characters from the *permitted set*.   |
| `type`       | "Container"        
|              | _in addition to the standard set above_ |               |
| `name`       | The original name, which may contain any UTF-8 character. Often this will be the same as the last path element of the `id`, but it does not have to be. |
| `containers` | A list of the immediate child containers, if any. All members are of type `Container` or `ArchivalGroup`. Within an ArchivalGroup, `containers` can only have other `Container` objects as members. |
| `binaries`   | A list of the immediate contained binaries, if any. All members are of type `Binary`. Binaries cannot exist outside of an Archival Group. |
| `partOf`     | The `id` of the ArchivalGroup the Container is in. Not present if the Container is outside an ArchivalGroup. |

Browsing the repository via the API means following links to child Binaries and Containers, recursively.

The root of the repository is itself a `Container`, at https://preservation-api.library.leeds.ac.uk/repository. However, this has the special `type` value `RepositoryRoot`. Visiting that URL with appropriate credentials will show the child Containers of the root in the `containers` property of the JSON response, which in turn allows you to browse down through the hierarchy of containers into Archival Groups, and within Archival Groups, into further containers and binaries.


### 📄 Binary

For representing a file: any kind of file stored in the repository. 

 - Binaries can only exist within ArchivalGroups
 - You add or patch binaries by referencing files in S3 by their URIs in an ImportJob, rather than directly passing binary payloads to the API. You can't POST binary file contents to the API.

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1/my-directory/My_File.pdf",
    "type": "Binary",
    "name": "My File.pdf",
    "contentType": "application/pdf",
    "digest": "b6aa90e47d5853bc1b84915f2194ce9f56779bc96bcf48d122931f003d62a33c",
    "origin": "s3://dlip-working-bucket/deposits/e5tg66hn/my-directory/My_File.pdf",
    "size": 15986,
    "content": "https://preservation-api.library.leeds.ac.uk/content/example-objects/ArchivalGroup1/my-directory/My_File.pdf?version=v2",
    "partOf": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1"
}
 ```

| Property     | Description                       | 
| ------------ | --------------------------------- |
| `id`         | URI of the Binary in the API. The path may only contain characters from the *permitted set*.   |
| `type`       | "Binary"                       |
|              | _in addition to the standard set above_ |
| `name`       | The original name, which may contain any UTF-8 character. |
| `contentType`| The internet type of the file, e.g., `application/pdf`. The Preservation platform will usually deduce this for you, it is not required on ingest. Also known as "mime type". |
| `digest`     | The SHA-256 checksum for this file. This is required and is always present on a Binary when sending to the API or retrieving from the API. There are additional API services to determine checksums of files. |
| `origin`     | The S3 URI within a Deposit where this file may be accessed. For a Binary within an Archival Group, this is the the location in the underlying repository storage (i.e., it is already preserved). If importing and sending this data to the API as part of an ImportJob, this is the S3 location the API should read the file from.  |
| `size`       | The size of the file in bytes.    |
| `content`    | An endpoint from which the binary content of the file may be retrieved (subject to authorisation). This is always provided by the API for API users to read a single file (it's not a location for the API to fetch from). |
| `partOf`     | The `id`  of the ArchivalGroup the Binary is in. Never null when returned by the API. Not required when sending as part of an ImportJob. |

> [!IMPORTANT]
> The `origin` property of a preserved Binary exposes the underlying storage location in the OCFL file layout. It is a deliberate design decision to surface this information rather than obfuscate the actual locations of files. That doesn't mean you can necessarily access it - it's likely that very few callers would have access to this location, but those that need it (e.g., providing runtime access to content) can use it as they need. The file content may be stored at multiple locations (e.g., backups, replication) but the `origin` property only gives one value.
> The `content` property streams the content from the `origin` location (and is also subject to access restrictions), but many applications are better served by dealing with files at source (in S3 or on a file system) as they see fit, rather than introduce an intermediate stream over HTTP into any access scenario.



### 📦 ArchivalGroup

A preserved ArchivalGroup - e.g., the files that comprise a digitised book, or a manuscript, or a born digital item. an ArchivalGroup might only have one file, or may contain hundreds of files and directories (e.g., digitised images and mets.xml). an ArchivalGroup is the unit of versioning - files within an ArchivalGroup cannot be separately versioned, only the ArchivalGroup as a whole.

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1",
    "type": "ArchivalGroup",
    "name": "My ArchivalGroup", 
    "version": {
       "ocflVersion": "v2",
       "mementoDateTime": "2024-03-14T14:58:58",
       "mementoTimestamp": "20240314145858"
    },
    "versions": [
      {
       "ocflVersion": "v1",
       "mementoDateTime": "2024-03-12T12:00:00",
       "mementoTimestamp": "20240312120000"
      },
      {
       "ocflVersion": "v2",
       "mementoDateTime": "2024-03-14T14:58:58",
       "mementoTimestamp": "20240314145858"
      }
    ],
    "storageMap": { },  // see StorageMap section later
    "containers": [],   
    "binaries": []       
}
```

## Browsing the repository

<!--
GET /repository/{*path} 
⎔ Preservation.API.Features.Repository.RepositoryController::Browse([FromRoute] string? path = null, [FromQuery] string? view = null, [FromQuery] string? version = null)
-->

To retrieve the repository root, containers, ArchivalGroups and Binaries within an Archival Group, callers send HTTP GET requests. The repository can be navigated starting from the root and following the hierarchy of Containers and Binaries returned in each resource. The following examples assume the caller has permission to see all the resources:

```
// Get the repository root:
GET /repository

// pick a Container from the "containers" list:
GET /repository/library

// Navigate into a further container:
GET /repository/library/manuscripts

// Request an ArchivalGroup within that container
GET /repository/library/manuscripts/ms-342

// Special parameter on the ArchivalGroup: view the METS XML directly
GET /content/library/manuscripts/ms-342?view=mets

// Request a Container within that ArchivalGroup:
GET /repository/library/manuscripts/ms-342/objects

// ...and a Binary within that Container:
GET /repository/library/manuscripts/ms-342/objects/34r.tiff


```

* All of the above requests will return the latest version of the resource. 
* A Container will include its nested _**immediate**_ children in the `containers` and `binaries` properties.
* An Archival Group response includes _**all**_ descendant Containers and Binaries - the entire object, no matter how deep, is returned in a single JSON payload.
* You can also retrieve any Container or Archival Group _without_ its immediate child resources (`containers` and `binaries` are always empty) by appending `?view=lightweight` to the request.
* The `version` query string parameter is only supported when the `view` parameter has the value `lightweight`. Previous versions of Archival Groups are viewed using the OCFL endpoint below.


```
// Request a lightweight view of an Archival Group (no child resources returned)
GET /repository/library/manuscripts/ms-342?view=lightweight

// Request a lightweight view at a particular version:
GET /repository/library/manuscripts/ms-342?version=v2&view=lightweight

// TODO
// Get the actual bytes of the preserved object (subject to permissions)
GET /content/library/manuscripts/ms-342/objects/34r.tiff?version=v2

```

### Additional GET parameters

| Parameter    | Description                       | 
| ------------ | --------------------------------- |
| `view`       | Valid values are:<br/>`mets` - only valid as GET on Archival Group, and returns the XML content of the METS file.<br/>`lightweight` - valid for Containers and Archival Groups, and returns a single object where the child `containers` and `binaries` properties are empty lists - always unpopulated. |  
| `version`    | Only valid when the `view` parameter is "lightweight". If the resource is an archival group, the value is a string in either the OCFL version format ("v1", "v2", "v3" etc) or the Memento timestamp format ("20250311111913"). If the resource is anything else, only the Memento format is currently supported. |

> [!WARNING]
> TODO - Ideally the OCFL format is supported for all resource requests, and the memento format is deprecated. You can find the memento format by asking for the Archival Group's Storage Map (see later).


### HEAD requests

<!-- 
HEAD /repository/{*path} 
⎔ Preservation.API.Features.Repository.RepositoryController::HeadResource([FromRoute] string path)
-->

HEAD requests to the same resource path as above work as expected, but with some additional features. They can be used to efficiently determine whether a resource exists, and also its `type`. A HEAD request will return one of the status codes 200, 404, 401 and 410 - where 410 is HTTP "Gone" - a resource _used to exist_ at this URI but does no longer. This kind of response is called a **tombstone** and corresponds to the same [concept in Fedora](https://wiki.lyrasis.org/display/FEDORA6x/Delete+vs+Purge).

In addition, if the response status code is HTTP 200, the response will include an HTTP Header `X-Preservation-Resource-Type` that gives the `type` value of the resource - "Container", "Binary" or "ArchivalGroup".


### Create a Container with PUT

<!--
PUT /repository/{*path} 
⎔ Preservation.API.Features.Repository.RepositoryController::CreateContainer([FromRoute] string? path = null, [FromBody] Container? container = null)
-->

This is only allowed outside of an ArchivalGroup, to create repository structure.

The body can be a container:

```
PUT /repository/library/c20-printed-books
{
  "type": "Container",
  "name": "20th Century Printed Books"
}
```

Or you can omit the body, and the container name will be derived from the path:

```
PUT /repository/library/c20-printed-books
```

The response is `201 Created` with the new Container resource in the body and its `id` property in the `Location` header.


### Delete a Container

<!--
DELETE /repository/{*path} 
⎔ Preservation.API.Features.Repository.RepositoryController::DeleteContainer([FromRoute] string path, [FromQuery] bool purge)
-->

A container may only be deleted if it is empty.

```
DELETE /repository/library/c20-printed-books?purge=true
```

The `purge` parameter removes the Container completely. Without it, a _tombstone_ HTTP 410 response will be returned for subsequent GET requests to the Container URI, and the API will prevent a resource being created at that path.

You can also do this in two steps - DELETE without purge (leaving a tombstone), and then later sending another DELETE with the purge parameter to remove the resource completely. The URI will then return a 404, and another Container may be created at the same path.



## Deposit

A working set of files in S3, which:

* will become an ArchivalGroup that doesn't yet exist
* or can be used for updating an ArchivalGroup
* or can be used to obtain the files in an Archival Group for other purposes (e.g. just to look at them).

The latter two are deposits created by Exports.

API users ask the Preservation API to create a Deposit, which returns an identifier and a _*Workspace*_ in S3 (an S3 key prefix under which to assemble files). The Workspace belongs exclusively to one Deposit, but other processes external to the Preservation API can (and must) add and remove files and folders to the Workspace.

> [!NOTE]
> A Deposit is a wrapper around a group of files that are intended to become an Archival Group (imported into Preservation) or are the content of an Archival Group at a particular version (an export). You create a Deposit to make the initial Archival Group in, then run an import job which makes the Archival Group. Later, perhaps to add a file, you export the Archival Group into a new Deposit.

The Preservation API does not itself offer a direct way to upload the binary content of a file into S3 (or any other Deposit backing storage). You can't POST binary data to an API endpoint. It's assumed that your applications do that independently - assemble files in the workspace allocated to them by the API. Your applications may also provide their own METS file to describe the contents, which the Preservation API can read to look for checksums and other information. The Preservation API can also create and edit METS files for you, and has API operations to add and remove files and folders to the METS file. The Preservation API can only modify METS files it has created; you can't introduce a third party METS file and modify it via API operations. You'd have to modify it manually, updating the METS file in the workspace yourself. 

> [!NOTE]
> If the Preservation API is managing METS, you might upload some files to the workspace (via AWS S3 APIs, or FTP, or whatever) and then send a list of those files to a Preservation API endpoint to add them to the METS file. Later you might send another list to remove files from METS. 


> [!TIP]
> For .NET implementations, the [WorkspaceManager](04-Workspace-Manager.md) class provides functions to manage the contents of a deposit. Most of those functions are exposed in the HTTP API of the Preservation API, but can be used in independent applications. Both the Presentation API and the [Preservation UI](05-Preservation-UI.md) use this class to manage the file system and edit the METS file.



### Creating a new Deposit

<!--
POST /deposits                  
⎔ Preservation.API.Features.Deposits.DepositsController::CreateDeposit([FromBody] Deposit deposit)
-->

POST a minimal Deposit body to `https://preservation-api.library.leeds.ac.uk/deposits` and the API will create a new Deposit, assigning a URI (the `id` property).

In this example the intended ArchivalGroup URI, the name of the ArchivalGroup, and a note are all provided up front. These three fields are optional - you can also create a Deposit without any information about where it is to go or what it is called, and decide on these later.

Request

```
POST /deposits HTTP/1.1
Host: preservation-api.library.leeds.ac.uk
// (other headers omitted)
{
  "type": "Deposit",
  "template": "BagIt",
  "archivalGroup": "https://preservation-api.library.leeds.ac.uk/repository/library/my-new-archivalgroup",
  "archivalGroupName": "My new Archival Group",
  "submissionText": "A note for me and my colleagues later"
}
```

Response

```
HTTP/1.1 201 Created
Location: https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg
// (other headers omitted)
```

The deposit at the provided `Location` will look like this:


```
GET /deposits/e56fb7yg HTTP/1.1
Host: preservation-api.library.leeds.ac.uk
(other headers omitted)
```

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg",
    "type": "Deposit",  
    "archivalGroup": "https://preservation-api.library.leeds.ac.uk/repository/library/my-new-archivalgroup",
    "archivalGroupExists": false,
    "archivalGroupName": "My new Archival Group",
    "submissionText": "A note for me and my colleagues later",
    "files": "s3://dlip-working-bucket/deposits/e56fb7yg/",
    "status": "new",
    "active": "true",
    "preserved": null,
    "preservedBy": null,
    "versionPreserved": null,
    "exported": null,
    "exportedBy": null,
    "versionExported": null,
    "metsETag": "hg67fghufp2jiefho875",
    "lockedBy": null,
    "lockDate": null,
    "pipelineJobs": [],

    // The common resource fields:    
    "created": "2024-03-14T14:58:46.102335Z",    
    "createdBy": "https://preservation-api.library.leeds.ac.uk/users/tom",
    "lastModified": "2024-03-14T14:58:46.102335Z",
    "lastModifiedBy": "https://preservation-api.library.leeds.ac.uk/users/tom"
}
```

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `id`                  | URI of the Deposit in the API. This is always assigned by the API.   |
| `type`                | "Deposit"                       |
| `template`            | This is a write-only property supplied when creating a new Deposit. Values are "None" (the default), "RootLevel" and "BagIt". If `RootLevel` the API wil create an `objects` directory, a `metadata` directory and a METS file that references the two directories. If `BagIt` the same layout is produced but one level down inside a `data` directory. If you have a BagIt bag to upload, choose this layout.                   |
| `archivalGroup`       | The URI of the ArchivalGroup in the repository that this deposit will become (or was exported from).<br>You don't need to provide this up front. You may not know it yet (e.g., you are appraising files). For some users, it will be assigned automatically. It may suit you to set this shortly before sending the deposit for preservation.                   |
| `archivalGroupExists` | Whether the resource at `archivalGroup` exists (i.e., the Deposit will update it, rather than create it)  |
| `archivalGroupName`   | The name of the ArchivalGroup. If new, this will be given to a new Archival Group when created by an Import Job generated from this Deposit. It is not required (it can be set on the ImportJob directly), but is useful for clarity.  |
| `submissionText`     | A space to leave notes for colleagues or your future self |
| `files`               | An S3 key prefix that represents a parent location. Use the _Workspace_ under this key to assemble files for an ImportJob. |
| `status`              | Usually "new" when a Deposit is created. If you requested this deposit to be created from an existing ArchivalGroup as an export (see export below), then you need to wait until this status becomes "new" before you can be sure that all the files are in S3. You won't be able to do any work from the deposit until this happens. Possible values are "exporting", "new" and "preserved".  When you create a Deposit for an existing Archival Group by POSTing to /deposits, this is *not* an export and the status will be "new" immediately. |
| `active`             | Whether the Deposit is editable (can be worked on). Once an import job has run for a deposit it is no longer active, but still may be retrieved from the API for a time (lifecycle policies may remove the deposit completely after an extended period). |
| `preserved`          | Timestamp indicating when an import job from this deposit resulted in a new ArchivalGroup or new version of an ArchivalGroup.  |
| `preservedBy`        | URI of the user/api caller that executed the import job. |
| `versionPreserved`   | The OCFL version (e.g., "v1", "v2", "v3") that resulted from this Deposit   |
| `exported`           | If this deposit was created as a result of asking the API to export an ArchivalGroup, the date that happened.  |
| `exportedBy`         | Who triggered the export |
| `versionExported`    | ...and the version of the ArchivalGroup that was exported then.  |
| `metsETag`           | The Preservation API supports operations to modify the METS file (adding/removing files or folders), and you can also edit the Deposit contents, including the METS file, independently of the Preservation API. Either way, you will need to supply this ETag value to update the METS file, and your changes will be rejected if it is no longer valid for the workspace (someone else has edited the METS file)  | 
| `lockedBy`           | URI of a user/api caller that is holding a lock on the Deposit, preventing modification. Usually null - a lock is not required to edit, only to stop others from editing. |
| `lockDate`           | If `lockedBy` is not null, a timestamp indicating when that user acquired the lock. |

### More on templates

When the `template` property value is "None", you are in complete control of the file structure of the deposit, and can arrange files how you like. The Preservation API will look for a METS file in the root from which it can derive the necessary SHA256 checksums for the files, and optional additional metadata such as the name of the file. If you then ask the API to generate an import job it will use this METS-derived data.

If you create your own import job manually, you can supply checksums at this point, and the Deposit content can be anything.

If the backing store is S3, the Preservation API can also read SHA256 checksums from S3 Object Attributes, but only if this attribute has been set. If you are not providing a checksum via METS and want the Preservation API to create an import job for you, you will have to upload files to S3 with the `ChecksumAlgorithm` parameter set to `SHA256`. See [Checking object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html) on AWS.

When providing your own METS to supply this information, the METS file must include (at least) SHA256 checksums for the deposit files, as `premis` metadata:

```
<premis:fixity>
   <premis:messageDigestAlgorithm xsi:type="premis:messageDigestAlgorithm">SHA256</premis:messageDigestAlgorithm>
   <premis:messageDigest>49ea24a3070c92a393289685ad9d3c3d71e5c23f0ac72e76e63aac658dc3ee59</premis:messageDigest>
</premis:fixity>
```

When the `template` property is "RootLevel" the Deposit will be created like this:

```
/
   objects/
   metadata/
   mets.xml
```

(The objects and metadata folder are empty)

And when the `template` property is "BagIt", the Deposit will be created like this:

```
/
  data/
    objects/
    metadata/
    mets.xml
```

This form is ideal for upload an unpacked BagIt bag into - and the Preservation API will read any BagIt manifest file in the root of this structure and use checksums from it. The Preservation API will also read the outputs of various tools if they are placed in specific subfolders under `metadata/`.

For more information see the section *Processing tool outputs* below.

> [!WARNING]
> (Need more explanation about processing tool outputs - needs its own section)


### Special Deposit Creation from identifier

<!--
POST /deposits/from-identifier                  
⎔ Preservation.API.Features.Deposits.DepositsController::CreateDepositFromIdentifier([FromBody] SchemaAndValue schemaAndValue)
-->

The Preservation API has a specific integration with the Leeds identity service, allowing a Deposit to be created for an Archival Group from just an identifier. Instead of POSTing a deposit body to /deposits, you POST a `SchemaAndValue` to /deposits/from-identifier:


| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `schema`              | Any schema identifier supported by Leeds Identity Service |
| `value`               | A URI, or for certain schemas, just a single string identifier |
| `template`            | Same as the Deposit `template` property |    

Request

```
POST /deposits/from-identifier HTTP/1.1
Host: preservation-api.library.leeds.ac.uk

{
   "schema": "id",
   "value": "t2sjhy5d",
   "template": "None"
}
```

Response

```
HTTP/1.1 201 Created
Location: https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg
// (other headers omitted)
```

The resulting Deposit will have its `archivalGroup` and `archivalGroupName` properties already populated. This is typically used when all the files, including METS, sill be supplied externally and the Preservation API won't manage the METS file.

  
### Working on a Deposit

You can do whatever you like in the S3 space provided by a deposit. Upload new files to S3, rearrange the files, etc.

Most clients will also include a METS file, and the Preservation API will use that METS file to obtain, if possible, expected digest (SHA256) checksums for each file, original names of files and directories, and content types (mime types) of files. This additional information is required for constructing an Import Job. The places the Preservation API looks for this information in a METS file are described later.

If you are not using a METS file, or are using a METS file that the Preservation API does not understand, you must provide digest information another way - by asking AWS to compute a SHA256 checksum when uploading a file - [AWS docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html).

You can also supply them in an Import Job as described below.

Most of the work done on a deposit is in S3, placing files. You can also modify the Deposit, providing (or updating) the `ArchivalGroup`, `submissionText` and `status` fields (the API can also set the status field itself). To perform an Import Job on a deposit, it must have had its `ArchivalGroup` property set, but _when_ in the workflow this happens is up to you.


### Fetch an individual Deposit

<!--
GET /deposits/{id}         
⎔ Preservation.API.Features.Deposits.DepositsController::GetDeposit([FromRoute] string id)
-->

Deposits are always at the path `/deposits/<identifier>`

```
GET /deposits/e56fb7yg
```

The response will be in the form of the example above.


### Fetch METS XML for deposit

<!--
GET /deposits/{id}/mets    
⎔ Preservation.API.Features.Deposits.DepositsController::GetDepositMets([FromRoute] string id) 
-->

```
GET /deposits/e56fb7yg/mets
```

This additional path parameter will return an XML response which is the content of the METS file. This doesn't have to be a Preservation-API specific METS file; the API will return the content of the first file in the root of the deposit that it recognises as a METS file. It looks for a file in the root called "mets.xml" by preference, and then for .xml files that contain the string "mets" (case-insensitive) in their filenames.


### Listing and searching Deposits

<!--
GET /deposits    
⎔ Preservation.API.Features.Deposits.DepositsController::ListDeposits([FromQuery] DepositQuery? query)
-->

The API provides an extensive set of query parameters for retrieving deposits.

```
// By default will return the first page of 100 results, ordered by created date descending, for active deposits only.
GET /deposits

// Page 37 of results created by a user matching the string "tom"
GET /deposits?page=37&createdBy=tom
```

Supported query parameters are:

| Query parameter       | Type      | Default   | Description       | 
| --------------------- | --------- | --------- | ----------------- |
| `page`                | integer   | `1`       | The page of results, from 1 to whatever. |
| `pageSize`            | integer   | `100`     | How many results to return in each response. |
| `orderBy`             | string    | `created` | Can take `archivalGroupPath`, `status`, `exported`, `exportedBy`, `preserved`, `preservedBy`, `lastModified`, `lastModifiedBy`, `created`, `createdBy`. |
| `ascending`           | boolean   | `false`   | Controls direction of `orderBy`  |
| `createdBy`           | string*   | null      | constrains results to those created by the user supplied. |
| `createdAfter`        | iso date  | null      | constrains results to those created after the date supplied. |
| `createdBefore`       | iso date  | null      | constrains results to those created before the date supplied. |
| `lastModifiedBy`      | string*   | null      | constrains results to those last modified by the user supplied. |
| `lastModifiedAfter`   | iso date  | null      | constrains results to those last modified after the date supplied. |
| `lastModifiedBefore`  | iso date  | null      | constrains results to those last modified before the date supplied. |
| `preservedBy`         | string*   | null      | constrains results to those preserved by the user supplied. |
| `preservedAfter`      | iso date  | null      | constrains results to those preserved after the date supplied. |
| `preservedBefore`     | iso date  | null      | constrains results to those preserved before the date supplied. |
| `exportedBy`          | string*   | null      | constrains results to those exported by the user supplied. |
| `exportedAfter`       | iso date  | null      | constrains results to those exported after the date supplied. |
| `exportedBefore`      | iso date  | null      | constrains results to those exported before the date supplied. |
| `archivalGroupPath`   | string    | null      | returns only Deposits for the specific archival group.  |
| `status`              | string    | null      | returns only Deposits with the supplied status "new", "exporting", "preserved".  |
| `showAll`             | boolean   | `false`   | by default only active deposits are returned, this overrides that behaviour. |


*This can be a user URI or just the "slug" name part.


### Patching a Deposit

<!--
PATCH /deposits/{id}
⎔ Preservation.API.Features.Deposits.DepositsController::PatchDeposit([FromRoute] string id, [FromBody] Deposit deposit)
-->

This is used to update the fields `archivalGroup`, `archivalGroupName` and `submissionText` only.

```
PATCH /deposits/e56fb7yg
{
    "id": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg",
    "type": "Deposit",  
    "archivalGroup": "https://preservation-api.library.leeds.ac.uk/repository/library/my-new-archivalgroup",
    "archivalGroupName": "A Better name",
    "submissionText": "I changed my mind about the name."
}
```


### Deleting a Deposit

<!--
DELETE /deposits/{id}
⎔ Preservation.API.Features.Deposits.DepositsController::DeleteDeposit([FromRoute] string id)
-->

A Deposit can be deleted at any time, for example, to start again on a Deposit, or to abandon one.

```
DELETE /deposits/e56fb7yg
```

* Deleting a Deposit has no effects on an ArchivalGroup already created from it.
* Inactive deposits are _automatically_ deleted from S3 working space after a specific time (TBC - e.g., 1 year)
* A Deposit is not a preserved resource like a Container, Binary or ArchivalGroup. That is, it's not in Fedora. Therefore the discussion about tombstones and purging above does not apply.


### Export: creating a deposit from an existing ArchivalGroup

<!--
POST /deposits/export
⎔ Preservation.API.Features.Deposits.DepositsController::ExportArchivalGroup([FromBody] Deposit deposit)
-->

This is when you want access to the files of an ArchivalGroup in S3, usually because you want to make an update but could be for any purpose. You may be an API client that has access to the working S3 space but not to the underlying Fedora repository (almost certainly!). While you can request an individual HTTP response for any Binary via the `content` property, sometimes you want the whole object to work on.

To do this you POST a non-empty Deposit body to `/deposits/export`:

```
POST /deposits/export HTTP/1.1
Host: preservation-api.library.leeds.ac.uk
(other headers omitted)

{
  "type": "Deposit",
  "archivalGroup": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup2",
  "versionExported": "v2"
}
```

If `versionExported` is omitted (which will usually be the case) the latest version is exported to create a new Deposit. 

The POST returns a new Deposit object as a JSON body, which includes the S3 location in the `files` property. While the Deposit object is returned immediately, it's not complete until its `status` property is "new" - you can check by polling the Deposit resource at intervals. Only after this happens are the files available in S3 (at the location given by `files`). You might see files arriving in S3 while this happens, but you can't do any work with the Deposit until it is at the "new" status.


### Locking a Deposit

<!--
POST /deposits/{id}/lock
⎔ Preservation.API.Features.Deposits.DepositsController::CreateLock([FromRoute] string id, [FromQuery] bool force = false)
-->

A lock is more of a marker on a Deposit than something that can prevent all activity. The API expects you to work on files in a Deposit location independently, and can have no visibility of your activity until an explicit refresh of its view of storage is asked for. Access to the working location is an AWS or file system concern, not an API concern.

However, the deposit locking mechanism has two purposes:

* User interfaces built on top of the API, used by those without direct access to the deposit working location, can use the lock status to enforce more constraints on user behaviour.
* The API can prevent direct actions on a locked deposit where the action is requested by someone other than the lock holder - patches, modification of METS files via API, and creaton of Import Jobs.

You can work on a Deposit without acquiring a lock on it.

```
POST /deposits/e56fb7yg/lock
```

This will change the values of the Deposit's `lockedBy` and `lockDate` properties, until a further update is made. The identity of the caller becomes the `lockedBy` property. If the Deposit is already locked by someone else, this will return an HTTP 409 Conflict response. You can override this behaviour by adding the `force` query string parameter:

```
POST /deposits/e56fb7yg/lock?force=true
```

That will acquire a lock for the caller, whether or not the Deposit is already locked.


### Unlocking a Deposit

<!--
DELETE /deposits/{id}/lock
⎔ Preservation.API.Features.Deposits.DepositsController::DeleteLock([FromRoute] string id)
-->

Any API caller can remove a lock:

```
DELETE /deposits/e56fb7yg/lock
```

If there is no existing lock, the operation is a no-op rather than an error.


## Working with Deposit files and folders

The files and folders in a Deposit are not quite the same as Containers and Binaries. They will _become_ Containers and Binaries when imported into an Archival Group, and will have been Containers and Binaries before being exported into a Deposit. But they have different data requirements, especially when tool output metadata is present.

Inside a Deposit, the files and folders are represented by a different pair of resource types:


### WorkingDirectory

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `type`                | "WorkingDirectory"                |
| `localPath`           | The path of the directory relative to the root of the Deposit. Examples are "objects", "objects/images", or "data/objects" in a BagIt template layout. Never has a leading slash. |
| `name`                | The name of the directory, which may be different from the last path element. This is typically used to store the original name of a directory. |
| `modified`            | Timestamp indicating the last modified date of the directory |
| `metsExtensions`      | A set of additional metadata for the directory that relate to specific METS concepts. See **MetsExtensions** below. |
| `metadata`            | A list of *Metadata* resources for the directory. These metadata reflect information the Preservation API can see in tool outputs in the metadata/ folder, and/or BagIt manifest data the Preservation API can see in the root of the Deposit when it has the BagIt template layout. They are used to add to METS, or reflect what's in METS. See *File and Directory Metadata* below. |
| `accessRestrictions`  | A list of strings that represent access conditions on this directory. They might be derived from METS, or might be waiting to be applied to METS. They can be overridden by child access restrictions. |
| `rightsStatement`     | A single URI from a controlled vocabulary of rights statements, that applies to the contents of this directory until overridden in child files and directories.  |
| `files`               | A list of **WorkingFile** resources contained in this directory. See next section. |
| `directories`         | A list of **WorkingDirectory** resources contained in this directory. |


### WorkingFile

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `type`                | "WorkingFile"                |
| `contentType`         | The internet type (aka mime type) of the file. |
| `digest`              | The SHA256 checksum of the file. |
| `size`                | The size in bytes of the file. |
| `localPath`           | The path of the file relative to the root of the Deposit. Examples are "objects/images/image_001.tiff", "mets.xml", or "data/mets.xml" in a BagIt template layout. Never has a leading slash. |
| `name`                | The name of the file, which may be different from the last path element. This is typically used to store the original name of a file. |
| `modified`            | Timestamp indicating the last modified date of the file |
| `metsExtensions`      | A set of additional metadata for the file that relate to specific METS concepts. See **MetsExtensions** below. |
| `metadata`            | A list of **Metadata** resources for the file. These metadata reflect information the Preservation API can see in tool outputs in the metadata/ folder, and/or BagIt manifest data the Preservation API can see in the root of the Deposit when it has the BagIt template layout. They are used to add to METS, or reflect what's in METS. See *File and Directory Metadata* below. |
| `accessRestrictions`  | A list of strings that represent access conditions on this specific file. They might be derived from METS, or might be waiting to be applied to METS. |
| `rightsStatement`     | A single URI from a controlled vocabulary of rights statements, that applies to this file.  |


### MetsExtensions

A resource that is the value of the `metsExtensions` property of **WorkingDirectory** or **WorkingFile**. This is never supplied by the caller, it is always generated by the API to reflect the relationship between the working file structure and the METS file.

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `physDivId`           | The XML ID attribute of the mets:div for the file or directory in the METS structMap (type physical)  |
| `admId`               | The XML ID attribute of the administrative metadata element for the file or directory. |              
| (more to follow)      | (...)                             |


### Metadata

There are several different types of metadata resource that can be listed under the `metadata` property of **WorkingFile** or **WorkingDirectory**.

The following two fields are common to all types of Metadata:

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `source`              | The tool or process that generated the metadata, e.g., "Siegfried" or "BagIt". |
| `timestamp`           | A timestamp indicating when the metadata was generated. |

Different types of metadata have additional properties as appropriate:

#### Digest Metadata

Typically derived from tool outputs that only provide the checksum. A `source` value might be `BagIt`.

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `type`                | "DigestMetadata"                  |
| `digest`              | The SHA256 checksum of the file.  |


#### File Format Metadata

Metadata generated by a tool such as Siegfried that provides PRONOM-based file format identification. A `source` might also be "Brunnhilde" if run by that tool.

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `type`                | "FileFormatMetadata"              |
| `digest`              | The SHA256 checksum of the file.  |
| `size`                | The size in bytes of the file.    |
| `pronomKey`           | The PRONOM key, e.g., "fmt/353"   |
| `formatName`          | The friendly name of the format, e.g., "Tagged Image File Format"  |
| `contentType`         | The internet type (mime type), e.g., "image/tiff"  |
| `originalName`        | The relative of the file at the time the tool analysed it. |
| `storageLocation`     | The fully qualified location of the file at the time the tool analysed it. |


#### EXIF Metadata

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `type`                | "ExifMetadata"                    |
| (tbc)                 | ...                               |


#### Virus Scan Metadata

| Property              | Description                       | 
| --------------------- | --------------------------------- |
| `type`                | "VirusScanMetadata"               |
| (tbc)                 | ...                               |


> [!WARNING]
> Some further work is needed to rationalise the use of access conditions and rights statements


An example of a WorkingFile with two types of metadata:

```json
{
  "type": "WorkingFile",
  "metadata": [
    {
      "type": "DigestMetadata",
      "source": "BagIt",
      "timestamp": "2025-07-30T15:46:31.7401058Z",
      "digest": "0298a9c0bf853aaaca9e95dc4c0d0d769b66347102dea65ba6ede6fce1548162"
    },
    {
      "type": "FileFormatMetadata",
      "source": "Brunnhilde",
      "timestamp": "2025-07-30T15:46:31.7401058Z",
      "digest": "0298a9c0bf853aaaca9e95dc4c0d0d769b66347102dea65ba6ede6fce1548162",
      "size": 7686654,
      "pronomKey": "fmt/1507",
      "formatName": "Exchangeable Image File Format (Compressed)",
      "originalName": null,
      "storageLocation": null,
      "contentType": "image/jpeg"
    }
  ],
  "localPath": "data/objects/nyc/DSCF1156.JPG",
  "name": null,
  "modified": "2025-05-05T13:35:00Z",
  "accessRestrictions": [],
  "rightsStatement": null,
  "contentType": "image/jpeg",
  "digest": "0298a9c0bf853aaaca9e95dc4c0d0d769b66347102dea65ba6ede6fce1548162",
  "size": 7686654
}
```

### Viewing what's in the Deposit

<!--
GET /deposits/{id}/filesystem
⎔ Preservation.API.Features.Deposits.DepositsController::GetFileSystem([FromRoute] string id, [FromQuery] bool refresh = false)
-->

The types **WorkingDirectory**, **WorkingFile** and the additional metadata types are not constructed by API callers, they are only _returned by the API when it reports on the contents of a deposit:

```
// return the cached view of the file system of the Deposit
GET /deposits/e56fb7yg/filesystem

// force a refresh of the Deposit file system
GET /deposits/e56fb7yg/filesystem?refresh=true
```

This returns a **WorkingDirectory** resource, with recursive child WorkingDirectory and WorkingFile resources (each with their own `metadata` properties), describing the complete contents of the Deposit workspace.

The `metadata` is derived from any **tool outputs** the Preservation API finds in the Deposit, as described later.

Typical uses for this filesystem view might be:

* Generating a user interface for navigating the Deposit
* Comparing what's in the Deposit with what's in the METS file

> [!TIP]
> If you are working in .NET, the WorkspaceManager class offers more functionality for working with the contents of the METS file and the contents of the workspace directly.


### Modifying the METS file

A typical workflow for a set of files you want to preserve as an Archival Group files you might involve:

* Creating a new Deposit with the RootLevel or BagIt templates, which gives you an `objects/` directory, a `metadata/` directory, and a METS file - all unpopulated.
* Arranging the files under an `objects/` directory in an _external environment_ such as BitCurator, then performing some analysis on the files using **tools**, saving the tool outputs into known locations under a `metadata/` folder, and then uploading the files and their metadata as a package to the S3 location of the Deposit (see [RFC 006 for details](../rfcs/006-pipelines-and-outputs.md#workflow)), OR
* Uploading the files to the S3 location of the Deposit and then asking the Preservation API to run a pre-configured set of tools over them (see pipelines below).

You then end up with, in the Deposit:

* A set of files under the `objects/` folder - i.e., the files you want to preserve as a logical unit, as an Archival Group
* A set ot tool outputs under the `metadata/` folder, that provide further information about those files, such as format identification, EXIF data, virus reports
* (and if BagIt layout, with `objects/` and `metadata/` under `data/`, a set of BagIt files in the root including the BagIt manifest)

If you requested a view of the Deposit on the /deposit/{id}/filesystem endpoint, you'd see not just the file and folder layout but also the detailed metadata for each file (`WorkingFile`) collated from the various tool outputs. All this metadata is information that should be stored as part of the preserved digital object, in METS form.

However, the METS file is still the original, unpopulated one - nothing has happened to 

There are two reasons for this.

* In the first workflow scenario, where the analysis is performed externally, there has been no interaction with the Preservation API at all in the construction of a fully populated Deposit with objects/ files and metadata/.
* Even in the second scenario, where the Preservation API ran the tools, you might not want all the files to be part of the eventual preserved object.

For these reasons the synchronisation of the Deposit contents with the METS file is a separate operation:

<!--
POST /deposits/{id}/mets
⎔ Preservation.API.Features.Deposits.DepositsController::AddItemsToMets([FromRoute] string id, [FromBody] List<string> localPaths)
-->

```
POST /deposits/e56fb7yg/mets
If-Match: "bfc13a64729c4290ef5b2c2730249c88ca92d82d"

[
  "metadata/brunnhilde/siegfried.csv",
  "metadata/brunnhilde/logs/viruscheck-log.txt",
  "objects/image_001.tif",
  "objects/image_002.tif",
  "objects/docs/Fedora-Usage-Principles.doc",
  "objects/docs/tuesday/notes.txt"
]
```

Note that the caller must supply an [If-Match](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-Match) HTTP Header whose value is the METS file ETag. The METS file ETag can be obtained from the Deposit object's `metsETag` property; it is also returned as the `ETag` HTTP response header from the direct view of the METS file at `/deposits/{id}/mets`.

The body is a JSON list of strings, where the strings are the relative paths of the files and/or folders to be added. Adding a folder on its own does not add its contents; all intended files must be listed.

On receiving this payload the Preservation API adds (or updates) the entries for the files in the METS file, including all relevant metadata.



> [!TIP]
> For .NET implementations, the [WorkspaceManager](04-Workspace-Manager.md) class can perform these actions for you - building a list of files and directories currently not in METS but to be added, and then adding them directly. This functionality is used by the Preservation API.

#### Removing items from METS and the Deposit

The deletion of files from the Deposit and/or the METS is a little more complicated. You can delete files from the Deposit workspace location independently of the API, but API helps with simultaneous deletions from the Deposit and/or from METS. The scenarios are:

* deleting a file that is in the Deposit workspace but has not been added to METS
* deleting a file from METS that is not currently in the Deposit workspace (this happens on updates where the full contents were not exported)
* deleting a file from both the METS and the Deposit workspace

Rather than POST a list of paths as strings, you POST a `DeleteSelection` resource. 

> [!WARNING]
> `deleteFromDepositFiles` and `deleteFromMets` are not independent operations - if `deleteFromDepositFiles` is false, nothing will happen. The Preservation API will always try to delete from the Deposit. Is that the desired behaviour?

| Property                  | Description                       | 
| ------------------------- | --------------------------------- |
| `deleteFromDepositFiles`  | boolean. The items will be removed from the Deposit workspace. |
| `deleteFromMets`          | boolean. The items will **also** be removed from METS, if present. This has no effect if `deleteFromDepositFiles` is false.  |
| `items`                   | List of minimal items:   |

Each entry in `items` requires just two fields:

| Property                  | Description                       | 
| ------------------------- | --------------------------------- |
| `path`                    | The relative path of the file or directory  |
| `isDir`                   | boolean - required - you need to confirm that the path is a directory (when it is) |


A typical delete operation might then be (note POST not DELETE, and `.../mets/delete` not `.../mets`):

<!--
POST /deposits/{id}/mets/delete
⎔ Preservation.API.Features.Deposits.DepositsController::DeleteItemsToMets([FromRoute] string id, [FromBody] DeleteSelection deleteSelection)
-->

```
POST /deposits/e56fb7yg/mets/delete
If-Match: "bfc13a64729c4290ef5b2c2730249c88ca92d82d"

{
  "deleteFromMets": true,
  "deleteFromDepositFiles": true,
  "items": [
    {
      "path": "objects/unwanted-folder",
      "isDir": true
    },
    {
      "path": "objects/unwanted-folder/unwanted-file.txt",
      "isDir": false
    },
    {
      "path": "objects/files/unwanted-1.txt",
      "isDir": false
    },
    {
      "path": "objects/files/unwanted-2.txt",
      "isDir": false
    }
  ]
}
```

While you do need to supply child file paths (you can't supply just a folder path where there are child items), the Preservation API will take care of the order of delete operations, deleting the child items first. Delete operations that cannot be supported result in a HTTP 400 Bad Request.



## ImportJob

An ImportJob is a statement, in JSON form, of what changes you want carried out. Containers to add, Containers to delete, Binaries to add, Binaries to delete, Binaries to update (patch).

If you are using the Deposit as an assembly area for files, you can ask the Preservation API to build an ImportJob for you, from the content of the Deposit in S3. You can also ask it to build and execute the ImportJob in a single operation. This is a "diff" import job - the Preservation API compares what's in the Deposit with what's in the current Archival Group (if there is one) and prepares the changes required to bring the new Archival Group about.

An automated diff isn't always desirable - you might create a Deposit for the purposes of making an edit to a single file (e.g., a METS file), and the content of the Deposit might be just that one file you want to change - and not necessarily sitting in the Deposit at the correct relative path. In this scenario, if you asked the platform to generate a diff ImportJob, it would see the mostly empty S3 working space and produce an ImportJob with many Containers to delete and many Binaries to delete. It would have been better to construct the ImportJob manually and specify just the one Binary to patch - giving both the `id`  property of the Binary - its repository address - and the `location` property - the S3 URI.

It is a little more nuanced than this. The Deposit doesn't have to contain all the files in order for the correct diff to be constructed, if they are mentioned in the METS file. 

> [!IMPORTANT]
> An Import Job is a means of synchronising a deposit with the repository, whether the deposit represents the new state in its entirety, or is partial. Even if the only operations you want to perform in an Import Job are deletions, you still need a Deposit to give the ImportJob context - to launch it from - and for auditing.

Before you can ask for an Import Job, the `ArchivalGroup` field of the Deposit must have been set - otherwise the API has nothing to compare it with. This applies to a new Deposit where no ArchivalGroup yet exists - you're effectively comparing your S3 files with an empty object, but the API needs to know where you want to put the new object.

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg/importJobs/diff",
    "type": "ImportJob",
    "deposit": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg",
    "ArchivalGroup": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup2",
    "ArchivalGroupName": "Manuscript 2024-b",
    "sourceVersion": {
       "name": "v2",
       "date": "2024-03-14T14:58:58"
    },
    "containersToAdd": [
      {
        "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1/my-directory/bar",
        "name": "bar"
      },      
    ],
    "binariesToAdd": [
      {
        "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1/my-directory/foo.jpg",
        "name": "foo.jpg",
        "digest": "b6aa90e47d5853bc1b84915f2194ce9f56779bc96bcf48d122931f003d62a33c",
        "location": "s3://dlip-working-bucket/deposits/e56fb7yg/my-directory/foo.jpg"
      },
      {
        "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1/my-directory/bar/strasse.xml",
        "name": "straße.xml",
        "digest": "2c9eaa2a0080b9e20b481e7550c64096dd12731c574b8884a280b4b3fe8fd40e",
        "location": "s3://dlip-working-bucket/deposits/e56fb7yg/my-directory/bar/stra___.xml"
      }
    ],
    "containersToDelete": [],
    "binariesToDelete": [      
      {
        "id": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup1/my-directory/unwanted.txt",
      }
    ],
    "binariesToPatch": []
}
```

| Property           | Description                       | 
| ------------------ | --------------------------------- |
| `id`               | The URI this import job was obtained from, OR your own identifier for it if generated manually or edited. This URI has no special significance for _processing_ the job.  |
| `type`             | "ImportJob"                       |
| `deposit`          | The Deposit that was used to generate this job, and to which it will be sent if executed. The job must be POSTed to the value of this property plus `/importJobs` |
| `ArchivalGroup`    |  The object in the repository that the job is to be performed on. This object doesn't necessarily exist yet - this job might be creating it. The value must match the `ArchivalGroup` of the deposit, so it's technically redundant, but must be included so that the intent is explicit and self-contained. |
| `ArchivalGroupName`|  The display name of the ArchivalGroup, required when creating a new one. |
| `sourceVersion`    | Always provided when you ask the API to generate an ImportJob as a diff and the ArchivalGroup already exists. May be null for a new object.* |
| `containersToAdd`  | A list of Container objects to be created within the ArchivalGroup. The `id`  property gives the URI of the container to be created, whose path must be "within" the ArchivalGroup and must only use characters from the permitted set. The `name` property of the container may be any UTF-8 characters, and can be used to preserve an original directory name. |
| `binariesToAdd`  | A list of Binary objects to be created within the ArchivalGroup from keys in S3. The `id`  property gives the URI of the binary to be created, whose path must be "within" the ArchivalGroup and must only use characters from the permitted set. The `name` property of the Binary may be any UTF-8 characters, and can be used to preserve an original file name. The `location` must be an S3 key within the Deposit. The `digest` is only required if the SHA256 cannot be obtained by the API from METS file information or from S3 metadata. All API-generated jobs will include this field. Note that in the second example above, the URI last path element, the `name` property, and the S3 location last path element are all different - this is permitted, although perhaps unusual. |
| `containersToDelete` | A list of containers to remove. `id`  is the only required property. The Containers must either be already empty, or only contain Binaries mentioned in the `binariesToDelete` property of the same ImportJob. |
| `binariesToDelete` | A list of binaries to remove. `id`  is the only required property.  |
| `binariesToPatch`  | A list of Binary objects to be updated within the ArchivalGroup from keys in S3. The `id`  property gives the URI of the binary to be patched, which must already exist. The `name` property of the Binary may be any UTF-8 characters, and can be used to preserve an original file name. This may be different from the originally supplied `name`. The `location` must be an S3 key within the Deposit. The `digest` is only required if the SHA256 cannot be obtained by the API from METS file information or from S3 metadata. |


> ❓* Do we require the version to be specified (and require it to be the current version) if you've manually built an ImportJob? As a means of avoiding conflicts? "I think I'm basing this job on v2, I didn't realise the object was at v7 because Fred has been fiddling about with it".

> ❓What kind of safeguards do we want? e.g., if you specify a binary to delete that isn't there, is that an error? Obviously any binariesToAdd that aren't there is an error. What if you specify a binary to add that's already there? Error - use binariesToPatch instead. Do you need to provide the binary+digest in S3 if you ONLY want to patch the `name` property?

> ❓In the storage API prototype there are separate path properties for location within the object. Here, we use the fully qualified URI for everything, in the '@id` property: `https://preservation-api.library.leeds.ac.uk/<path/in/repository>/<path/within/object>`. This is harder to manage, callers will have to construct more, but it avoids any repetition and is always explicit. Is it usable though?

### Generate Import Job

Requesting an Import Job to be created from the files in S3 makes no changes to any state, and is retrieved with a GET:

```
GET /deposits/e56fb7yg/importJobs/diff HTTP/1.1
Host: preservation-api.library.leeds.ac.uk
```

```jsonc
{
   // similar to example above
}
```

The Import Job is generated from multiple sources:

- The layout of files in S3
- The METS file in that layout, if present: the API looks for a METS file in specific locations. 
- SHA256 checksums in the METS, and/or...
- SHA256 checksums in AWS S3 object metadata
- Content type information in the METS
- File and Directory name information in the METS (if present)
- File and Directory (S3 Object) key names in S3 (will be normalised to reduced character set for the `id`  properties of Containers and Binaries within the Ingest Job and therefore within the resulting ArchivalGroup)


> ❓ Goobi always brings its own METS file. Other contributing processes will bring theirs.

You can of course generate this JSON manually. As mentioned it's not required that the `id`  values of your Containers and Binaries in the intended ArchivalGroup match the source S3 file structure; this will always be the case if you requested an Import Job from the API but may not convenient for a single file update deep within the structure.


### Execute import job

Whether generated for you or manually created, you need to POST a JSON payload to `<deposit-uri>/importJobs`.

```
POST /deposits/e56fb7yg/importJobs HTTP/1.1
Host: preservation-api.library.leeds.ac.uk

(the Import Job JSON body, as above)
```

There is a special case where you don't need to see or edit the diff-generated Import Job. In this case the body POSTed to the .../importJobs endpoint comprises ONLY the special .../diff ID:

```jsonc
{
  "id": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg/importJobs/diff"
}
```

This payload is an instruction to the API to synchronise the ArchivalGroup with the S3 contents of the deposit, in a single action. It's a Bad Request if the single `id`  in the JSON doesn't share the same deposit path it's POSTed to.

In all cases, the resource returned from submitting an ImportJob is an `ImportJobResult`.

> ❓ Do we need a better name than ImportJob?  

## ImportJobResult

> ❓ Some validation can happen on immediate receipt of the POST - e.g., JSON is well formed, can be parsed into expected objects, has expected deposits, etc. But some probably has to wait until the job is actually picked up - even checking digests, checking for file presence in both S3 and Storage API. We won't begin any fedora transaction until processing actually starts, which means that in theory the job may have been valid when submitted but is no longer (two people are having a go...) I think we don't want excessive locking, we are optimistic but fail quickly on any problem. Maybe this is why you have to provide the `sourceVersion`.

This resource is returned quickly, before the ImportJob actually runs. The ImportJob may take a long time to run, be sitting in a queue, or otherwise not available for a while. You can repeatedly GET an ImportJob to check its progress. It will be at status "waiting" until it is picked up for processing.

```jsonc
{
    "id": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg/importJobs/results/ad5fbm8k",
    "type": "ImportJobResult",
    "importJob": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg/importJobs/ad5fbm8k",
    "originalImportJobId": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg/importJobs/diff",
    "deposit": "https://preservation-api.library.leeds.ac.uk/deposits/e56fb7yg",
    "ArchivalGroup": "https://preservation-api.library.leeds.ac.uk/repository/example-objects/ArchivalGroup2",
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

| Property           | Description                       | 
| ------------------ | --------------------------------- |
| `id`               | The URI of this ImportJobResult. You can poll this (with GET) to check for progress, using the fields below. |
| `type`             | "ImportJobResult"             |
| `importJob`        | A URI minted by the API which shows you the ImportJob submitted, for which this is the result. This is newly minted by the API when you actually submit an ImportJob, because: 1) not all Import Jobs are actually executed; 2) It may have been the special `.../diff` ImportJob; 3) It may have been an external identifier you provided.           |
| `originalImportJobId` | The `id`  property of the original submitted job |
| `deposit`             | Explicitly included for convenience; the deposit the job was started from. |
| `ArchivalGroup`       | Also included for convenience, the repository object the changes specified in the job are being applied to. |
| `status`              | One of "waiting", "running", "completed", "completedWithErrors" |
| `dateBegun`           | Timestamp indicating when the API started processing the job. Will be null/missing until then. |
| `dateFinished`        | Timestamp indicating when the API finished processing the job. Will be null/missing until then. |
| `newVersion`          | The version of the ArchivalGroup this job caused to be produced. Not known until the job has finished processing * |
| `errors`              | A list of errors encountered. These are error objects, not strings. (to be documented) |
| `containersAdded`     | Populated once the job has finished successfully. |
| `binariesAdded`       | Populated once the job has finished successfully. |
| `containersDeleted`   | Populated once the job has finished successfully. |
| `binariesDeleted`     | Populated once the job has finished successfully. |
| `binariesPatched`     | Populated once the job has finished successfully. |

NB the shared property `created` is a timestamp indicating when the API received the initial POST of the job.

> ❓ * can we know it earlier than that? 



## Exports



## StorageMap


## Versions





## Example Actions


### Navigating the repository

> RESTfully follow links with HTTP GETs, starting at the repository root `https://preservation-api.library.leeds.ac.uk/repository/`

We also need to search the repository, with filtering - "I can't browse to it, I don't know where it is" - or "there are 500,000 objects in this folder"

### Create a Container in the repository

> Goobi might not need to do this, if there is a default container associated with a client, or it is _assigned_ an ArchivalGroup.

### Find a deposit

(find work that needs your attention)

> Browse but also Search

### View recent deposits

- (User activity stream)
- (System activity stream)


<hr>

> ❓ What follows below is less developed...


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

## Pipelines

### Run pipeline

(Goobi will not do this)

METS options

## Associating identifiers from other systems

(interaction with id service - but how much of that is visible to callers?)

(should API callers be interacting with the id service themselves?)

### With Deposits

 - initial bundle of files 

### With ArchivalGroups

 - now in the Repository

## Managing ArchivalGroups

### Splitting an object into two

A special kind of import job? POST to a ../split endpoint? Does it need a Deposit?

A managed dual Deposit - user could do this manually by:

 - Exporting to a Deposit D1
 - Creating a new second deposit D2
 - copying subset of files from D1's S3 to D2's S3
 - Create an ImportJob from D1 that deletes those containers and binaries
 - Create an ImportJob (auto) from D2 that adds the copied files to a new ArchivalGroup

The Preservation API could assist in this process with a formal "split" operation.

What happens to the old version - persist in Fedora as distinct object?

### Merging two ArchivalGroups

If an object is to be merged with **part** of another object, that other object should be split first.



## PUT of binaries

Sequence diagram 3 for API clients who don't have S3 access, need way of putting to deposit via API.





> ❓the Preservation API does not need to expose all the OCFL details. Should the Preservation API expose the `origin` property? Or is the DLCS-syncing code also a direct consumer of the Storage API? If we hide `origin` then the only S3 paths in responses are for import and export operations which is cleaner. I think we should not expose underlying storage information in the Preservation API.


## Summary of HTTP API

<!--
/repository/{*path} 
⎔ Preservation.API.Features.Repository.RepositoryController::
GET    => Browse([FromRoute] string? path = null, [FromQuery] string? view = null, [FromQuery] string? version = null)
HEAD   => HeadResource([FromRoute] string path)
PUT    => CreateContainer([FromRoute] string? path = null, [FromBody] Container? container = null)
DELETE => DeleteContainer([FromRoute] string path, [FromQuery] bool purge)
-->

<!--
⎔ Preservation.API.Features.Deposits.DepositsController::
POST   /deposits                  => CreateDeposit([FromBody] Deposit deposit)
POST   /deposits/from-identifier  => CreateDepositFromIdentifier([FromBody] SchemaAndValue schemaAndValue)
GET    /deposits/{id}             => GetDeposit([FromRoute] string id)
GET    /deposits/{id}/mets        => GetDepositMets([FromRoute] string id) 
GET    /deposits                  => ListDeposits([FromQuery] DepositQuery? query)
PATCH  /deposits/{id}             => PatchDeposit([FromRoute] string id, [FromBody] Deposit deposit)
DELETE /deposits/{id}             => DeleteDeposit([FromRoute] string id)
POST   /deposits/export           => ExportArchivalGroup([FromBody] Deposit deposit)
POST   /deposits/{id}/lock        => CreateLock([FromRoute] string id, [FromQuery] bool force = false)
DELETE /deposits/{id}/lock        => DeleteLock([FromRoute] string id)
GET    /deposits/{id}/filesystem  => GetFileSystem([FromRoute] string id, [FromQuery] bool refresh = false)
POST   /deposits/{id}/mets        => AddItemsToMets([FromRoute] string id, [FromBody] List<string> localPaths)
POST   /deposits/{id}/mets/delete => DeleteItemsToMets([FromRoute] string id, [FromBody] DeleteSelection deleteSelection)

TODO:   
POST   /deposits/{id}/pipeline   => RunPipeline([FromRoute] string id, [FromQuery] string? runUser)
POST   /deposits/pipeline-status => LogPipelineRunStatus([FromBody] PipelineDeposit pipelineDeposit)

Omitted:
GET    /deposits/{id}/combined => GetCombinedDirectory([FromRoute] string id, [FromQuery] bool refresh = false)
-->


<!--
⎔ Preservation.API.Features.Activity.ActivityController::
GET    /archivalgroups/collection   => GetArchivalGroupsCollection()
GET    /archivalgroups/pages/{page} => GetArchivalGroupsPage()
POST   /archivalgroups/collection   => PushEventToStream([FromBody] Activity? activity)
-->


<!--
⎔ Preservation.API.Features.Agents.AgentsController::
GET    /agents => ListAgents()
-->


<!--
⎔ Preservation.API.Features.ImportJobs.ImportJobsController::
GET    /deposits/{depositId}/importjobs/diff                  => GetDiffImportJob([FromRoute] string depositId)
POST   /deposits/{depositId}/importjobs                       => ExecuteImportJob([FromRoute] string depositId, [FromBody] ImportJob importJob)
GET    /deposits/{depositId}/importjobs/results               => GetImportJobResult([FromRoute] string depositId)
GET    /deposits/{depositId}/importjobs/results/{importJobId} => GetImportJobResult([FromRoute] string depositId)
-->


<!--
⎔ Preservation.API.Features.Ocfl.OcflController::
GET    /ocfl/storagemap/{*path} => GetStorageMap([FromRoute] string path, [FromQuery] string? version = null)
-->


<!--
⎔ Preservation.API.Features.PipelineRunJobs.PipelineRunJobsController::
GET    /deposits/{depositId}/pipelinerunjobs/results => GetPipelineJobResults([FromRoute] string depositId)
-->


<!--
⎔ Preservation.API.Features.Search.SearchController::
GET    /search => Search(string text, int pageNumber = 0, int pageSize = 20, SearchType type = SearchType.All, int otherPage = 0)
-->


<!--
⎔ Preservation.API.Features.Validation.ValidationController::
GET    /validation/archivalgroup/{*archivalGroupPath} => TestArchivalGroupPath(string archivalGroupPath)
-->