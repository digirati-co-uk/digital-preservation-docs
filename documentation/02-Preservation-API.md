# Preservation API

_Throughout this document we will assume that the Preservation API root is at https://preservation.leeds.ac.uk. There is no API functionality at this root URI, however.

The Preservation API is consumed by the applications we build to implement Preservation tasks, and also by Goobi. Goobi uses it to preserve, and, sometimes, to recover a preserved _ArchivalGroup_ later for further work. Other applications use it either directly or via the Web UI for Preservation tasks, including evaluation of born digital material and collaboration with donors and other staff.

Whereas the [Storage API](03-Storage-API.md) is a wrapper around Fedora that bridges files-to-be-preserved to Fedora Archival Groups, so the Preservation API bridges Leeds business rules, models of digital objects and born digital workflow to the Storage API. These processes are then doubly insulated against the specifics of Fedora.

For example:

- The Storage API doesn't know what a METS file is, it's just another file being preserved as part of a _DigitalObject_.
- The Preservation API *does* know what a METS file is, and may use its contents (e.g., checksums, original file names) to construct calls to the Storage API.

However, there are concepts that are common to both, where the Preservation API is basically passing information from or to the Storage API. An example of this is browsing the repository via the API, which passes through (in simplified form) the Storage API concepts of Containers and Binaries.

> ❓The services for METS offered by the Preservation API are not detailed in this document; in this first version we will focus on Preservation of DigitalObjects. Similarly, interaction with EMu, splitting of Deposits and other specifically born digital flows are not covered - yet.

> ❓In the Storage API, there are different classes for modeling "folders" and "files" in the Fedora repository (`Container` and `Binary`) and for files and folders in transfer, for importing and exporting from S3 or other storage (`ContainerDirectory` and `BinaryFile`). I think the Preservation API can do away with this distinction for simplicity, but I've named _its_ concepts `Container` and `Binary` (and `DigitalObject` for Fedora's Archival Group). This means we have different classes with the same name in both APIs, but anyone who has used Fedora will understand what they are.

> ❓the Preservation API does not need to expose all the OCFL details. Should the Preservation API expose the `origin` property? Or is the DLCS-syncing code also a direct consumer of the Storage API? If we hide `origin` then the only S3 paths in responses are for import and export operations which is cleaner. I think we should not expose underlying storage information in the Preservation API.

This RFC deals with the Preservation API working on content in Amazon AWS S3, rather than on local file systems or other cloud storage providers. There is no reason why it couldn't support multiple protocols for the `location` property of a Binary and the `files` property of a Deposit, but we're going to implement S3 initially and it keeps this document simpler to limit it to that.

The Preservation API assumes that its callers have access to the AWS S3 working bucket(s), which is necessary to get content in or out.

## Authentication

The API implements a standard OAuth2 [Client Credentials Flow](https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/) for machine-to-machine access, with [Refresh Tokens](https://www.oauth.com/oauth2-servers/access-tokens/refreshing-access-tokens/) to ensure that access tokens are short lived and can be revoked.

Throughout this RFC the API is shown on the host name `preservation.dlip.leeds.ac.uk` - this is just for example.

> ❓For implementation we should get this working early on, when the API is just a hello-world - to avoid running into issues retrofitting it later.

## Resource Types

### Summary of resource types

 - **DigitalObject**: a preserved _thing_, a set of files in the repository. May be just one file, or may be thousands with a complex internal directory structure. Usually has a METS file that describes the object and provides technical, structural and administrative metadata.
 - **Container**: represents a directory or folder in the repository - both for folders within a DigitalObject, and for organisational structure in the repository above the level of a DigitalObject.
 - **Binary**: any file - text, images, datasets etc. Can only exist within a DigitalObject.
 - **Deposit**: a working set of files intended for Preservation (intended to become a DigitalObject) and also used for later updates to a DigitalObject.
 - **ImportJob**: a set of instructions to the Preservation API to create or modify a DigitalObject - the Containers and Binaries from a Deposit to preserve. For some workflows you might edit this manually but for others you might never need to see it.
 - **ImportJobResult**: a report on the execution of an ImportJob. It can be used to track an ongoing job as it is running, or for later examination.


### Common metadata

The resource types `Container`, `Binary`, `DigitalObject` and `Deposit` below all share a set of common properties:

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/...(path)...",
    "type": "(Resource)", // One of those below
    "created": "2024-03-14T14:58:46.102335Z",    // carries the original name of the directory
    "createdBy": "https://preservation.dlip.leeds.ac.uk/users/tom",
    "lastModified": "2024-03-28T12:00:00.00000Z",
    "lastModifiedBy": "https://preservation.dlip.leeds.ac.uk/users/donald",
    // ...
    // Other type-specific properties
    // ...
}
```

The resource types `ImportJob` and `ImportJobResult` also have the first four of these properties, but not `lastModified` and `lastModifiedBy` (as they cannot be modified).

| Property         | Description                       | 
| ---------------- | --------------------------------- |
| `@id`            | URI of the resource in the API. The path may only contain characters from the *permitted set*.   |
| `type`           | The type of the resource |
| `created`        | ISO 6801 DateTime string representing the creation date of the resource within the Preservation system (not its original external creation date). |
| `createdBy`      | A URI representing the user who created this resource (may be an API user) | 
| `lastModified`   | ISO 6801 DateTime string representing the last modified date of the resource within the Preservation system (not its original external last modified date). |
| `lastModifiedBy` | A URI representing the user who last modified this resource (may be an API user) |      


### 📁 Container

For building structure to organise the repository into a hierarchical layout. Containers also represent directories within a DigitalObject.

 - Only some API users can create Containers within the repository. Other users are given an existing Container, or set of Containers, that they can create DigitalObjects in.
 - Containers are also used to represent directories within a Digital Object, but no user of the API can create them inside a Digital Object directly. Instead they are created indirectly as part of an ImportJob - the ImportJob specifies `containersToAdd` (see below).

A Container retrieved while browsing the repository via the API might look like this:

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory",
    "type": "Container",
    "name": "my-dírèçtóry",    // carries the original name of the directory
    "containers": [],
    "binaries": [
        // ... see below  
    ],
    "partOf": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1"
}
```

| Property     | Description                       | 
| ------------ | --------------------------------- |
| `@id`        | URI of the Container in the API. The path part of this URI may only contain characters from the *permitted set*.   |
| `type`       | "Container"                       |
| `name`       | The original name, which may contain any UTF-8 character. Often this will be the same as the last path element of the `@id`, but it does not have to be. |
| `containers` | A list of the immediate child containers, if any. All members are of type `Container`. |
| `binaries`   | A list of the immediate contained binaries, if any. All members are of type `Binary`. |
| `partOf`     | The `@id` of the DigitalObject the Container is in. Not present if the Container is outside a DigitalObject. |

Browsing the repository via the API means following links to child Binaries and Containers, recursively.

### 📄 Binary

For representing a file: any kind of file stored in the repository. 

 - Binaries can only exist within DigitalObjects
 - You add or patch binaries by referencing files in S3 by their URIs in an ImportJob, rather than directly passing binary payloads to the API.

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory/My_File.pdf",
    "type": "Binary",
    "name": "My File.pdf",
    "contentType": "application/pdf",
    "digest": "b6aa90e47d5853bc1b84915f2194ce9f56779bc96bcf48d122931f003d62a33c",
    "location": "s3://dlip-working-bucket/deposits/e5tg66hn/my-directory/My_File.pdf",
    "content": "https://preservation.dlip.leeds.ac.uk/content/example-objects/DigitalObject1/my-directory/My_File.pdf",
    "partOf": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1"
}
 ```

| Property     | Description                       | 
| ------------ | --------------------------------- |
| `@id`        | URI of the Binary in the API. The path may only contain characters from the *permitted set*.   |
| `type`       | "Binary"                       |
| `name`       | The original name, which may contain any UTF-8 character. |
| `contentType`| The internet type of the file, e.g., `application/pdf`. The Preservation platform will usually deduce this for you, it is not required on ingest. |
| `digest`     | The SHA-256 checksum for this file. This will always be returned by the API, but is only required when **sending** to the API if the checksum is not provided some other way - see below. |
| `location`   | The S3 URI within a Deposit where this file may be accessed. If just browsing, this will be empty. If importing and sending this data to the API as part of an ImportJob, this is the S3 location the API should read the file from.  |
| `content`    | An endpoint from which the binary content of the file may be retrieved (subject to authorisation). This is always provided by the API for API users to read a single file (it's not a location for the API to fetch from) |
| `partOf`     | The `@id` of the DigitalObject the Binary is in. Never null when returned by the API. Not required when sending as part of an ImportJob. |


### 📦 DigitalObject

A preserved digital object - e.g., the files that comprise a digitised book, or a manuscript, or a born digital item. A DigitalObject might only have one file, or may contain hundreds of files and directories (e.g., digitised images and METS.xml). A DigitalObject is the unit of versioning - files within a DigitalObject cannot be separately versioned, only the DigitalObject as a whole.

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1",
    "type": "DigitalObject",
    "name": "My Digital Object", 
    "version": {
       "name": "v2",
       "date": "2024-03-14T14:58:58"
    },
    "versions": [
      {
       "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1?version=v1",
       "name": "v1",
       "date": "2024-03-12T12:00:00"
      },
      {
       "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1?version=v2",
       "name": "v2",
       "date": "2024-03-14T14:58:58"
      }
    ],
    "containers": [],    //
    "binaries": []       //  These behave as with Container and Binary above
}
```

> ❓What more do we actually need here? Is that all? If you want OCFL / Storage map info, as DLCS will, you have the Storage API. Purely Preservation consumers don't need any more than this.

#### Accessing previous versions

The `versions` property allows you to view previous versions of the object. The `content` property of Binaries returned in an explicit version will also carry an explicit version in their URIs.


### Deposit

> ❓I still have reservations about this name - it's a deposit when you're building something up for the first time, but is that still a sensible thing to call it later? Working files, working set, etc. 

A working set of files in S3, which will become a DigitalObject, or is used for updating a DigitalObject. API users ask the Preservation API to create a Deposit, which returns an identifier and a working area in S3 (a key under which to assemble files).

#### Creating a new deposit

POST an **empty** body to `https://preservation.dlip.leeds.ac.uk/deposits/` and the API will create a new Deposit, assigning a URI (from the ID service):

Request

```
POST /deposits HTTP/1.1
Host: preservation.dlip.leeds.ac.uk
(other headers omitted)
```

Response

```
HTTP/1.1 201 Created
Location: https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg
(other headers omitted)
```

The deposit at the provided `Location` will look like this (common user and date fields omitted as above):

```
GET /deposits/e56fb7yg HTTP/1.1
Host: preservation.dlip.leeds.ac.uk
(other headers omitted)
```

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg",
    "type": "Deposit",
    "digitalObject": null,
    "files": "s3://dlip-working-bucket/deposits/e56fb7yg/", // what to call this property?
    "status": "new",
    "submissionText": "",
    "datePreserved": null,
    "dateExported": null,
    "versionExported": null,
    "versionSaved": null,
    "pipelineJobs": []
}
```

| Property           | Description                       | 
| ------------------ | --------------------------------- |
| `@id`              | URI of the Deposit in the API. This is always assigned by the API.   |
| `type`             | "Deposit"                       |
| `digitalObject`   | The URI of the DigitalObject in the repository that this deposit will become (or was exported from).<br>You don't need to provide this up front. You may not know it yet (e.g., you are appraising files). For some users, it will be assigned automatically. It may suit you to set this shortly before sending the deposit for preservation. |
| `files`            | An S3 key that represents a parent location. Use the "space" under this key to assemble files for an ImportJob. |
| `status`           | TBC - a step in a workflow. If you requested this deposit to be created from an existing digital object (see Export below), then you need to wait until this status becomes "ready" before you can be sure that all the files are in S3. You won't be able to do any work from the deposit until this happens. |
| `submissionText`  | A space to leave notes for colleagues or your future self |
| `datePreserved`   | Timestamp indicating when this deposit was last used to create an ImportJob for the Respository*  |
| `dateExported`    | If this deposit was created as a result of asking the API to export a DigitalObject, the date that happened.  |
| `versionExported` | ...and the version of the Digital object that was exported then.  |
| `versionSaved`    | If an Import Job is created from the files in this deposit and then sent to Preservation, the version that was created. |
| `pipelineJobs`    | A list of jobs that have run on this deposit (TBC) |

> ❓* What's the relationship between a Deposit and an ImportJob? An ImportJob defines the creation or update of an ArchivalGroup; you might create an ImportJob based on some or all of the files in a Deposit - but there doesn't have to be a one-to-one between the files sitting in S3 under a deposit's files and the ImportJob that puts them into the Storage API - you might leave a few behind, deliberately, or might only need the Deposit and its S3 space to patch one file.

You can also POST a partial Deposit body to provide the Preservation URI or submission text at creation time:

Request

```
POST /deposits HTTP/1.1
Host: preservation.dlip.leeds.ac.uk
(other headers omitted)

{
  "digitalObject": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject2",
  "submissionText": "Just leaving this here"
}
```

> ❓Goobi doesn't need to use most of the functionality of a Deposit - that's for other bespoke applications. It really only uses it to acquire a working S3 space to assemble files.


#### Working on a deposit

You can do whatever you like in the S3 space provided by a deposit. Upload new files to S3, rearrange the files, etc.

Most clients will also include a METS file, and the Preservation API will use that METS file to obtain, if possible, expected digest (SHA256) checksums for each file, original names of files and directories, and content types (mime types) of files. This additional information is required for constructing an Import Job. The places the Preservation API looks for this information in a METS file are described later.

If you are not using a METS file, or are using a METS file that the Preservation API does not understand, you must provide digest information another way - by asking AWS to compute the checksum [AWS docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html).

You can also supply them in an Import Job as described below.

Most of the work done on a deposit is in S3, placing files. You can also modify the Deposit, providing (or updating) the `digitalObject`, `submissionText` and `status` fields (the API can also set the status field itself). To perform an Import Job on a deposit, it must have had its `digitalObject` property set, but _when_ in the workflow this happens is up to you.

You can also _split_ a deposit into two separate deposits (and more by repeating this action.)

> ❓The **split** instruction is probably an ImportJob with a different intent, that doesn't go to Preservation. "Do this to these files". Whether this is the same class or a very similar looking class is TBC - Goobi won't need this (I think) so we'll defer specification of splitting until later.


#### Export: creating a deposit from an existing digital object

This is when you want access to the files of a Digital Object in S3, usually because you want to make an update but could be for any purpose. You may be an API client that has access to the working S3 space but not to the underlying Fedora repository (almost certainly!). While you can request an individual HTTP response for any Binary, sometimes you want the whole object to work on.

To do this you POST a non-empty body to `/deposits/export`:

```
POST /deposits/export HTTP/1.1
Host: preservation.dlip.leeds.ac.uk
(other headers omitted)

{
  "digitalObject": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject2",
  "version": "v2"
}
```

If `version` is omitted (which will usually be the case) the latest version is exported to create a new Deposit. 

The POST returns a new Deposit object as a JSON body, which includes the S3 location in the `files` property. While the Deposit object is returned immediately, it's not complete until its `status` property is "ready" - you can check by polling. Only after this happens are the files available in S3 (at the location given by `files`). You might see files arriving in S3 while this happens, but you can't do any work with the Deposit until it is "ready".

> ❓Do we need an _ExportJobResult_? The Binary class has a `location` property, and I just removed this line from its description above: "If returned by the API as part of an export output, the location in S3 you can go to find the exported file." But now that export action returns a Deposit, which does not enumerate the files in JSON - you just go and look at them in S3. The Storage API does have this concept. Do we actually need it here? If so we could add an ExportResult resource type, which is included in a returned deposit when exported. 


### ImportJob

An ImportJob is like a diff - a statement, in JSON form, of what changes you want carried out. Containers to add, Containers to delete, Binaries to add, Binaries to delete, Binaries to update (patch).

If you are using the Deposit as an assembly area for files, you can ask the Preservation API to build an ImportJob for you, from the content of the Deposit in S3. You can also ask it to build and execute the ImportJob in a single operation.

This isn't always desirable - you might create a Deposit for the purposes of making an edit to a single file (e.g., a METS file), and the content of the Deposit might be just that one file you want to change - and not necessarily sitting in the Deposit at the correct relative path. In this scenario, if you asked the platform to generate an ImportJob, it would see the mostly empty S3 working space and produce an ImportJob with many Containers to delete and many Binaries to delete. It would have been better to construct the ImportJob manually and specify just the one Binary to patch - giving both the `@id` property of the Binary - its repository address - and the `location` property - the S3 URI.

An Import Job is a means of synchronising a deposit with the repository, whether the deposit represents the new state in its entirety, or is partial. Even if the only operations you want to perform in an Import Job are deletions, you still need a Deposit to give the ImportJob context - to launch it from - and for auditing.

Before you can ask for an Import Job, the `digitalObject` field of the Deposit must have been set - otherwise the API has nothing to compare it with. This applies to a new Deposit where no DigitalObject yet exists - you're effectively comparing your S3 files with an empty object.

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg/importJobs/diff",
    "type": "ImportJob",
    "deposit": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg",
    "digitalObject": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject2",
    "digitalObjectName": "Manuscript 2024-b",
    "sourceVersion": {
       "name": "v2",
       "date": "2024-03-14T14:58:58"
    },
    "containersToAdd": [
      {
        "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory/bar",
        "name": "bar"
      },      
    ],
    "binariesToAdd": [
      {
        "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory/foo.jpg",
        "name": "foo.jpg",
        "digest": "b6aa90e47d5853bc1b84915f2194ce9f56779bc96bcf48d122931f003d62a33c",
        "location": "s3://dlip-working-bucket/deposits/e56fb7yg/my-directory/foo.jpg"
      },
      {
        "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory/bar/strasse.xml",
        "name": "straße.xml",
        "digest": "2c9eaa2a0080b9e20b481e7550c64096dd12731c574b8884a280b4b3fe8fd40e",
        "location": "s3://dlip-working-bucket/deposits/e56fb7yg/my-directory/bar/stra___.xml"
      }
    ],
    "containersToDelete": [],
    "binariesToDelete": [      
      {
        "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory/unwanted.txt",
      }
    ],
    "binariesToPatch": []
}
```

| Property           | Description                       | 
| ------------------ | --------------------------------- |
| `@id`              | The URI this import job was obtained from, OR your own identifier for it if generated manually or edited. This URI has no special significance for _processing_ the job.  |
| `type`             | "ImportJob"                       |
| `deposit`          | The Deposit that was used to generate this job, and to which it will be sent if executed. The job must be POSTed to the value of this property plus `/importJobs` |
| `digitalObject`    |  The object in the repository that the job is to be performed on. This object doesn't necessarily exist yet - this job might be creating it. The value must match the `digitalObject` of the deposit, so it's technically redundant, but must be included so that the intent is explicit and self-contained. |
| `digitalObjectName`|  The display name of the Digital object, required when creating a new one. |
| `sourceVersion`    | Always provided when you ask the API to generate an ImportJob as a diff and the DigitalObject already exists. May be null for a new object.* |
| `containersToAdd`  | A list of Container objects to be created within the Digital object. The `@id` property gives the URI of the container to be created, whose path must be "within" the Digital Object and must only use characters from the permitted set. The `name` property of the container may be any UTF-8 characters, and can be used to preserve an original directory name. |
| `binariesToAdd`  | A list of Binary objects to be created within the Digital object from keys in S3. The `@id` property gives the URI of the binary to be created, whose path must be "within" the Digital Object and must only use characters from the permitted set. The `name` property of the Binary may be any UTF-8 characters, and can be used to preserve an original file name. The `location` must be an S3 key within the Deposit. The `digest` is only required if the SHA256 cannot be obtained by the API from METS file information or from S3 metadata. All API-generated jobs will include this field. Note that in the second example above, the URI last path element, the `name` property, and the S3 location last path element are all different - this is permitted, although perhaps unusual. |
| `containersToDelete` | A list of containers to remove. `@id` is the only required property. The Containers must either be already empty, or only contain Binaries mentioned in the `binariesToDelete` property of the same ImportJob. |
| `binariesToDelete` | A list of binaries to remove. `@id` is the only required property.  |
| `binariesToPatch`  | A list of Binary objects to be updated within the Digital object from keys in S3. The `@id` property gives the URI of the binary to be patched, which must already exist. The `name` property of the Binary may be any UTF-8 characters, and can be used to preserve an original file name. This may be different from the originally supplied `name`. The `location` must be an S3 key within the Deposit. The `digest` is only required if the SHA256 cannot be obtained by the API from METS file information or from S3 metadata. |


> ❓* Do we require the version to be specified (and require it to be the current version) if you've manually built an ImportJob? As a means of avoiding conflicts? "I think I'm basing this job on v2, I didn't realise the object was at v7 because Fred has been fiddling about with it".

> ❓What kind of safeguards do we want? e.g., if you specify a binary to delete that isn't there, is that an error? Obviously any binariesToAdd that aren't there is an error. What if you specify a binary to add that's already there? Error - use binariesToPatch instead. Do you need to provide the binary+digest in S3 if you ONLY want to patch the `name` property?

> ❓In the storage API prototype there are separate path properties for location within the object. Here, we use the fully qualified URI for everything, in the '@id` property: `https://preservation.dlip.leeds.ac.uk/<path/in/repository>/<path/within/object>`. This is harder to manage, callers will have to construct more, but it avoids any repetition and is always explicit. Is it usable though?

#### Generate Import Job

Requesting an Import Job to be created from the files in S3 makes no changes to any state, and is retrieved with a GET:

```
GET /deposits/e56fb7yg/importJobs/diff HTTP/1.1
Host: preservation.dlip.leeds.ac.uk
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
- File and Directory (S3 Object) key names in S3 (will be normalised to reduced character set for the `@id` properties of Containers and Binaries within the Ingest Job and therefore within the resulting DigitalObject)


> ❓ Goobi always brings its own METS file. Other contributing processes will bring theirs.

You can of course generate this JSON manually. As mentioned it's not required that the `@id` values of your Containers and Binaries in the intended digital object match the source S3 file structure; this will always be the case if you requested an Import Job from the API but may not convenient for a single file update deep within the structure.


#### Execute import job

Whether generated for you or manually created, you need to POST a JSON payload to `<deposit-uri>/importJobs`.

```
POST /deposits/e56fb7yg/importJobs HTTP/1.1
Host: preservation.dlip.leeds.ac.uk

(the Import Job JSON body, as above)
```

There is a special case where you don't need to see or edit the diff-generated Import Job. In this case the body POSTed to the .../importJobs endpoint comprises ONLY the special .../diff ID:

```jsonc
{
  "@id": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg/importJobs/diff"
}
```

This payload is an instruction to the API to synchronise the DigitalObject with the S3 contents of the deposit, in a single action. It's a Bad Request if the single `@id` in the JSON doesn't share the same deposit path it's POSTed to.

In all cases, the resource returned from submitting an ImportJob is an `ImportJobResult`.

> ❓ Do we need a better name than ImportJob?  

### ImportJobResult

> ❓ Some validation can happen on immediate receipt of the POST - e.g., JSON is well formed, can be parsed into expected objects, has expected deposits, etc. But some probably has to wait until the job is actually picked up - even checking digests, checking for file presence in both S3 and Storage API. We won't begin any fedora transaction until processing actually starts, which means that in theory the job may have been valid when submitted but is no longer (two people are having a go...) I think we don't want excessive locking, we are optimistic but fail quickly on any problem. Maybe this is why you have to provide the `sourceVersion`.

This resource is returned quickly, before the ImportJob actually runs. The ImportJob may take a long time to run, be sitting in a queue, or otherwise not available for a while. You can repeatedly GET an ImportJob to check its progress. It will be at status "waiting" until it is picked up for processing.

```jsonc
{
    "@id": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg/importJobs/results/ad5fbm8k",
    "type": "ImportJobResult",
    "importJob": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg/importJobs/ad5fbm8k",
    "originalImportJobId": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg/importJobs/diff",
    "deposit": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg",
    "digitalObject": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject2",
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
| `@id`              | The URI of this ImportJobResult. You can poll this (with GET) to check for progress, using the fields below. |
| `type`             | "ImportJobResult"             |
| `importJob`        | A URI minted by the API which shows you the ImportJob submitted, for which this is the result. This is newly minted by the API when you actually submit an ImportJob, because: 1) not all Import Jobs are actually executed; 2) It may have been the special `.../diff` ImportJob; 3) It may have been an external identifier you provided.           |
| `originalImportJobId` | The `@id` property of the original submitted job |
| `deposit`             | Explicitly included for convenience; the deposit the job was started from. |
| `digitalObject`       | Also included for convenience, the repository object the changes specified in the job are being applied to. |
| `status`              | One of "waiting", "running", "completed", "completedWithErrors" |
| `dateBegun`           | Timestamp indicating when the API started processing the job. Will be null/missing until then. |
| `dateFinished`        | Timestamp indicating when the API finished processing the job. Will be null/missing until then. |
| `newVersion`          | The version of the DigitalObject this job caused to be produced. Not known until the job has finished processing * |
| `errors`              | A list of errors encountered. These are error objects, not strings. (to be documented) |
| `containersAdded`     | Populated once the job has finished successfully. |
| `binariesAdded`       | Populated once the job has finished successfully. |
| `containersDeleted`   | Populated once the job has finished successfully. |
| `binariesDeleted`     | Populated once the job has finished successfully. |
| `binariesPatched`     | Populated once the job has finished successfully. |

NB the shared property `created` is a timestamp indicating when the API received the initial POST of the job.

> ❓ * can we know it earlier than that? 



## Example Actions


### Navigating the repository

> RESTfully follow links with HTTP GETs, starting at the repository root `https://preservation.dlip.leeds.ac.uk/repository/`

We also need to search the repository, with filtering - "I can't browse to it, I don't know where it is" - or "there are 500,000 objects in this folder"

### Create a Container in the repository

> Goobi might not need to do this, if there is a default container associated with a client, or it is _assigned_ a digitalObject.

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

#### Fixity information in Pronom

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

#### Original filename

> Goobi METS doesn't record this - use the name in S3; Archivematica METS records it as `LABEL` attribute on divs in physical structMap, we will do the same when we run our normalisation pipeline

TBC - Archivematica-esque example with struct divs of type File and Directory, with LABEL attributes.


#### File format identification

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

#### Content Type if possible

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

### With Digital Objects

 - now in the Repository

## Managing Digital Objects

### Splitting an object into two

A special kind of import job? POST to a ../split endpoint? Does it need a Deposit?

A managed dual Deposit - user could do this manually by:

 - Exporting to a Deposit D1
 - Creating a new second deposit D2
 - copying subset of files from D1's S3 to D2's S3
 - Create an ImportJob from D1 that deletes those containers and binaries
 - Create an ImportJob (auto) from D2 that adds the copied files to a new Digital Object

The Preservation API could assist in this process with a formal "split" operation.

What happens to the old version - persist in Fedora as distinct object?

### Merging two digital objects

If an object is to be merged with **part** of another object, that other object should be split first.



## PUT of binaries

Sequence diagram 3 for API clients who don't have S3 access, need way of putting to deposit via API.



