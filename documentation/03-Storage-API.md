# Storage API

The Storage API shares some concepts with the Preservation API - Containers, Binaries, Imports and Exports.

But it doesn't know about METS files and Deposits, or file format metadata or other tool outputs. Its job is to execute import jobs to store Binaries and Containers as Archival Groups, from whatever location you specify (as long as it can access it), and to export Archival Groups as files and directories to wherever you specify (again, as long as it has access).

Rather than repeat large amounts of the Preservation API documentation, this describes where they differ.

## Resource Types

[(Preservation API)](02-Preservation-API.md#resource-types)

The types are the same, except that their `id` properties will be on the Storage API host.


## Browsing the repository

[(Preservation API)](02-Preservation-API.md#browsing-the-repository)

The HTTP operations are the same, except that there is no `...?view=mets` parameter on an Archival Group request, because the Storage API has no concept of METS.

If you have permission to call the Storage API you can retrieve the binary content of any Binary (the Preservation API does not let you do this):

```
GET /content/library/manuscripts/ms-342/objects/34r.tiff
```

The path is the same as the repository path apart from the first element. This URI is exposed as the `content` property on a Binary in both APIs, but will return a forbidden status on the Preservation API.

## Deposit

There is no concept of a Deposit in the Storage API.

## Import Job

[(Preservation API)](02-Preservation-API.md#importjob)

The Storage API cannot generate a "diff" import job (or any kind of Import Job) for you. It can only execute Jobs that you create and send.

Whereas in the Preservation API all Import Jobs are in the context of a Deposit, the Storage API has a "universal" import endpoint:

```
POST /import
{
  "id": "https://example.org/any-unique-uri-you-like",
  "type": "ImportJob",
  "created": "2025-10-03T09:55:34.3621834Z",
  "archivalGroup": "https://storage-api/repository/kickoff/docs-misc/import-job-doc",
  "archivalGroupName": "Import job for Documentation",
  "sourceVersion": null,
  "ContainersToAdd": [
    {
      "id": "https://storage-api/repository/kickoff/docs-misc/import-job-doc/objects",
      "type": "Container",
      "name": "objects",
      "origin": "s3://any-accessible-bucket/any-path/objects"
    }
  ],
  "BinariesToAdd": [
    {
      "id": "https://storage-api/repository/kickoff/docs-misc/import-job-doc/objects/cat-uv.png",
      "type": "Binary",
      "name": "cat-uv.png",
      "origin": "s3://any-accessible-bucket/any-path/objects/cat-uv.png",
      "contentType": "image/png",
      "size": 449518,
      "digest": "1587a18ce3567215bfba9d0866b9e05e548b0ba70ab1b6e001a96a2f0e95c7f3"
    },
    {
      "id": "https://storage-api/repository/kickoff/docs-misc/import-job-doc/mets.xml",
      "type": "Binary",
      "name": "mets.xml",
      "origin": "s3://any-accessible-bucket/any-path/mets.xml",
      "contentType": "application/xml",
      "size": 3278,
      "digest": "2274bfad9b5420043fc62c6c34441ae436a0caab12d8a62a4679f4dfb2599e53"
    }
  ],
  "ContainersToDelete": [],
  "BinariesToDelete": [],
  "BinariesToPatch": [],
  "ContainersToRename": [],
  "BinariesToRename": []
}
```

As long as the `origin` properties of binaries are accessible by the Storage API it can stream content from them.

As with the Preservation API, an ImportJobResult is returned, and its `id` URI can be polled for completion in the same way.

## Exports

These work differently from the Preservation API. To begin an export, you POST an Export resource to /export:

```
POST /export
{
    "archivalGroup": "https://storage-api/repository/kickoff/docs-misc/import-job-doc",
    "destination": "s3://my-export-bucket/export-of-my-ag",
    "sourceVersion": "v15"
}
```

This returns an object of the same type - but fully populated:

```json
{
    "id": "https://storage-api/export/h6bb4dpm32",
    "archivalGroup": "https://storage-api/repository/kickoff/docs-misc/import-job-doc",
    "destination": "s3://my-export-bucket/export-of-my-ag",
    "dateBegun": "2025-10-03T09:55:34.3621834Z",
    "files": [],
    "errors": []
}
```

This can be polled until a non-null `dateFinished` property appears:

```
GET /export/h6bb4dpm32
```

```json
{
    "id": "https://storage-api/export/h6bb4dpm32",
    "archivalGroup": "https://storage-api/repository/kickoff/docs-misc/import-job-doc",
    "destination": "s3://my-export-bucket/export-of-my-ag",
    "sourceVersion": "v15",
    "dateBegun": "2025-10-03T09:55:34.3621834Z",
    "dateFinished": "2025-10-03T09:57:20.076543Z",
    "files": [
        "s3://my-export-bucket/export-of-my-ag/mets.xml",
        "s3://my-export-bucket/export-of-my-ag/objects/file1.doc"
    ],
    "errors": []
}
```


| Property           | Description                       | 
| ------------------ | --------------------------------- |
| `archivalGroup`    | The Storage API of the Archival Group to export |
| `destination`      | The S3 location or filesystem location to export to |
| `sourceVersion`    | The version of the Archival Group applied to - known at the start of processing |
| `dateBegun`        | Timestamp indicating when the API started processing the job. Will be null/missing until then. |
| `dateFinished`     | Timestamp indicating when the API finished processing the job. Will be null/missing until then. |
| `files`            | A list of all the files exported - S3 URIs, or filesystem paths |
| `errors`           | A list of errors encountered. These are [error objects](02-Preservation-API.md#error-object), not strings. |


## Activity Streams

[(Preservation API)](02-Preservation-API.md#activity-streams)

This is similar to the Preservation API, except that the stream reports on Import Jobs, not Archival Groups... it is a record of the Storage API's Import Job activity.

The Preservation API consumes it to produce a stream for Archival Groups.


```
GET /activity/importjobs/collection
```

This is the entry point to the single (for now) Activity Stream. It returns an `OrderedCollection` object:

```json
{
  "@context": "http://iiif.io/api/discovery/1/context.json",
  "id": "https://storage-api/activity/importjobs/collection",
  "type": "OrderedCollection",
  "totalItems": 3914,
  "first": {
    "id": "https://storage-api/activity/importjobs/1",
    "type": "OrderedCollectionPage"
  },
  "last": {
    "id": "https://storage-api/activity/importjobs/pages/40",
    "type": "OrderedCollectionPage"
  }
}
```

A client wishing to read the stream backwards to the last time they read it (or to the start) would load the `last` page:


```
GET /activity/importjobs/pages/40
```

```jsonc
{
  "@context": "http://iiif.io/api/discovery/1/context.json",
  "id": "https://storage-api/activity/importjobs/pages/40",
  "type": "OrderedCollectionPage",
  "startIndex": 3900,
  "prev": {
    "id": "https://storage-api/activity/importjobs/pages/39",
    "type": "OrderedCollectionPage"
  },  
  "orderedItems": [
    {
      "type": "Create",
      "object": {
        "id": "https://storage-api/import/results/m3cnbckjmtd9/cc/lqj7mqhg",
        "type": "ImportJobResult",
        "seeAlso": {
          "id": "https://storage-api/repository/cc/lqj7mqhg",
          "type": "ArchivalGroup"
        }
      },
      "endTime": "2025-10-06T10:34:19Z"
    }
  ],
  [
    {
      "type": "Update",
      "object": {
        "id": "https://storage-api/import/results/ec29ybrcz8rg/cc/abd321",
        "type": "ImportJobResult",
        "seeAlso": {
          "id": "https://storage-api/repository/cc/abd321",
          "type": "ArchivalGroup"
        }
      },
      "endTime": "2025-10-06T13:29:02Z"
    }
  ],
  // etc
}
```

...and then work from the end of the `orderedItems` list backwards until they come to an `endTime` before the last time they read the stream; they will then have gathered all the **new** events.

The value of `object` in this stream will always be an `ImportJobResult`, with a seeAlso property linking to the Archival Group affected by the Import Job.

## Agents

[(Preservation API)](02-Preservation-API.md#agents)

This section is the same as the Preservation API.

## StorageMap

[(Preservation API)](02-Preservation-API.md#storagemap)

This section is the same as the Preservation API.

