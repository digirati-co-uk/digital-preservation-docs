# Preservation API

The Preservation API is consumed by the applications we are going to build, and also by Goobi. Goobi uses it to preserve, and, sometimes, to recover a preserved _DigitalObject_ later for further work. Other applications use it either directly or via a Web UI for Preservation tasks, including evaluation of born digital material and collaboration with donors and other staff.

Whereas the [Storage API](002-storage-api.md) is a wrapper around Fedora that bridges files-to-be-preserved to Fedora ArchivalGroups, so the Preservation API bridges Leeds business rules, models of digital objects and born digital workflow to the Storage API.

For example:

- The Storage API doesn't know what a METS file is, it's just another file being preserved as part of a _DigitalObject_.
- The Preservation API *does* know what a METS file is, and may use its contents to construct calls to the Storage API.

However, there are concepts that are common to both, where the Preservation API is basically passing information from or to the Storage API. An example of this is browsing the repository via the API, which passes through (in simplified form) the Storage API concepts of Containers and Binaries.

> ❓The services for METS offered by the Preservation API are not detailed in this document; in this first version we will focus on Preservation of DigitalObjects. Similarly, interaction with EMu, splitting of Deposits and other specifically born digital flows are not covered - yet.

> ❓In the Storage API, there are different classes for modelling "folders" and "files" in the repository (`Container` and `Binary`) and for files and folders in transfer, for importing and exporting (`ContainerDirectory` and `BinaryFile`). I think the Preservation API can do away with this distinction for simplicity, but name _its_ concepts `Container` and `Binary` (and `DigitalObject` for Fedora's Archival Group). This means we have different classes with the same name in both APIs

> ❓the Preservation API does not need to expose all the OCFL details. Should the Preservation API expose the `origin` property? Or is the DLCS-syncing code also a direct consumer of the Storage API? If we hide `origin` then the only S3 paths in responses are for import and export operations which is cleaner.

The Preservation API assumes that its callers have access to the AWS S3 working bucket(s), which is necessary to get binary content in or out.

## Authentication

The API implements a standard OAuth2 [Client Credentials Flow](https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/) for machine-to-machine access, with [Refresh Tokens](https://www.oauth.com/oauth2-servers/access-tokens/refreshing-access-tokens/) to ensure that access tokens are short lived and can be revoked.

Throughout this RFC the API is shown on the host name `preservation.dlip.leeds.ac.uk` - this is just for example.

## Resource Types

### Common metadata

The resource types Container, Binary, DigitalObject and Deposit below all share a set of common properties:

```json5
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

 - Only some API users can create Containers within the repository. Other users are given an existing Container, or set of Containers, that they can create in.
 - Containers are also used to represent directories within a Digital Object, but no user of the API can create them inside a Digital Object directly. Instead they are created indirectly as part of an ImportJob.

A Container retrieved while browsing the repository via the API might look like this:

```json5
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
| `@id`        | URI of the Container in the API. The path may only contain characters from the *permitted set*.   |
| `type`       | "Container"                       |
| `name`       | The original name, which may contain any UTF-8 character. Often this will be the same as the last path element of the `@id`, but it does not have to be. |
| `containers` | A list of the immediate child containers, if any. All members are of type `Container`. |
| `binaries`   | A list of the immediate contained binaries, if any. All members are of type `Binary`. |
| `partOf`     | The `@id` of the DigitalObject the Container is in. Not present if the Container is outside a DigitalObject. |


### 📄 Binary

For representing a file, any kind of file stored in the repository. 

 - Binaries can only exist within DigitalObjects
 - You add or patch binaries by referencing files in S3 by their URIs in an ImportJob

```json5
{
    "@id": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject1/my-directory/My_File.pdf",
    "type": "Binary",
    "name": "My File.pdf",
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
| `digest`     | The SHA-256 checksum for this file. This will always be returned by the API, but is only required when sending to the API if the checksum is not provided some other way - see below. |
| `location`   | The S3 URI within a deposit where this file may be accessed. If just browsing, this will be empty. If importing and sending this data to the API as part of an ImportJob, this is the S3 location the API should read the file from. If returned by the API as part of an export output, the location in S3 you can go to find the exported file. |
| `content`    | An endpoint from which the binary content of the file may be retrieved (subject to authorisation). This is always provided by the API for API users to read a single file (it's not a location for the API to fetch from) |
| `partOf`     | The `@id` of the DigitalObject the Binary is in. Never null when returned by the API. Not required when sending as part of an ImportJob. |


### 📦 DigitalObject

A preserved digital object - e.g., the files that comprise a digitised book, or a manuscript, or a born digital item. A DigitalObject might only have one file, or may contain hundreds of files and directories (e.g., digitised images and METS.xml). A DigitalObject is the unit of versioning - files within a DigitalObject cannot be separately versioned, only the DigitalObject as a whole.

```json5
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

> ❓I still have reservations about this name - it's a deposit when you're building something up for the first time, but is that still a sensible thing to call it later?

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

```json5
{
    "@id": "https://preservation.dlip.leeds.ac.uk/deposits/e56fb7yg",
    "type": "Deposit",
    "digital_object": null,
    "files": "s3://dlip-working-bucket/deposits/e56fb7yg/", // what to call this property?
    "status": "new",
    "submission_text": "",
    "date_preserved": null,
    "date_exported": null,
    "version_exported": null,
    "version_saved": null,
    "pipeline_jobs": []
}
```

| Property           | Description                       | 
| ------------------ | --------------------------------- |
| `@id`              | URI of the Deposit in the API. This is always assigned by the API.   |
| `type`             | "Deposit"                       |
| `digital_object`   | The URI of the DigitalObject in the repository that this deposit will become (or was exported from).<br>You don't need to provide this up front. You may not know it yet (e.g., you are appraising files). For some users, it will be assigned automatically. It may suit you to set this shortly before sending the deposit for preservation. |
| `files`            | An S3 key that represents a parent location. Use the "space" under this key to assemble files for an ImportJob. |
| `status`           | TBC - a step in a workflow |
| `submission_text`  | A space to leave notes for colleagues or your future self |
| `date_preserved`   | Timestamp indicating when this deposit was last used to create an ImportJob for the Respository*  |
| `date_exported`    | If this deposit was created as a result of asking the API to export a DigitalObject, the date that happened.  |
| `version_exported` | ...and the version of the Digital object that was exported then.  |
| `version_saved`    | If an Import Job is created from the files in this deposit and then sent to Preservation, the version that was created. |
| `pipeline_jobs`    | A list of jobs that have run on this deposit (TBC) |

> ❓* What's the relationship between a Deposit and an ImportJob? An ImportJob defines the creation or update of an ArchivalGroup; you might create an ImportJob based on some or all of the files in a Deposit - but there doesn't have to be a one-to-one between the files sitting in S3 under a deposit's files and the ImportJob that puts them into the Storage API - you might leave a few behind, deliberately, or might only need the Deposit and its S3 space to patch one file.


You can also POST a partial Deposit body to provide the Preservation URI or submission text at creation time:

Request

```
POST /deposits HTTP/1.1
Host: preservation.dlip.leeds.ac.uk
(other headers omitted)

{
  "digital_object": "https://preservation.dlip.leeds.ac.uk/repository/example-objects/DigitalObject2",
  "submission_text": "Just leaving this here"
}
```

> ❓Goobi doesn't need to use most of the functionality of a Deposit - that's for other bespoke applications. It really only uses it to acquire a working S3 space to assemble files.


#### Working on a deposit






### ImportJob

An ImportJob is like a diff - a statement, in JSON form, of what changes you want carried out 
A means of synchronising a deposit with the repository

## Navigating the repository


## Actions

### Create a Container in the repository

> Goobi might not need to do this, if there is a default container associated with a client, or it is _assigned_ a Preservation Path

### Create a deposit for a new digital object

Ask for a deposit

get back id, preservation_path (if assigned), S3 location


### METS obligations

My METS, Your METS

Fixity information in Pronom

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

Original filename

> Goobi METS doesn't record this - use the name in S3; Archivematica METS records it as LABEL attribute on divs in physcial structMap, we will do the same when we run our normalisation pipeline

File format identification

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



Content Type if possible

Goobi does it like this:

```xml
<mets:fileSec>
    <mets:fileGrp USE="OBJECTS">
      <mets:file ID="FILE_0001_OBJECTS" MIMETYPE="image/jp2">
```

Archivematica only in tool output


### Run pipeline

(Goobi will not do this)

METS options


### Generate Import Job

From a deposit and therefore its files


### Execute import job

for a deposit


### Create a deposit for an existing digital object

ask for deposit passing preservation path of existing object


### Partial updates

You must supply a digest somehow. And if not in a METS file, it must be in S3 metadata.
You still need an ImportJob.

### Request a single binary

Is streamed to HTTP response


### Request an export to S3

Produces ExportResponse

### Find a deposit


### View recent deposits

(User activity stream)
(System activity stream)




Import Job

Deposit ID
Preservation Path
METS path
ImportJob properties
Client identity (user? Goobi is a user?)

METS requirements

PRONOM data for fixity

LABEL property of attributes


Individual Binary as stream


Export Job
Dump the whole object to an S3 location