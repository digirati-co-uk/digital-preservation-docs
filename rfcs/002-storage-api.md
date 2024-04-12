# Storage API

This RFC builds on [1. What is stored in Fedora](001-what-is-stored-in-fedora.md) which introduced the Storage API as a wrapper around Fedora to require callers to think in terms of whole digital objects.

This RFC describes the operations available in more detail, and accompanies the [sequence diagrams](../sequence-diagrams/README.md).

A key aspect of the storage API is that it neither accepts nor returns direct binary content - you can't POST binary content, nor does it serve it. Instead, both your request data and its response data has references to content locations (currently AWS S3 or local file paths are supported), and it is assumed that you have whatever separate access to those content locations you need to put files or fetch them.

You put content at a location and tell the API about it, and the API puts content at a location and tells you about it.

While filesystem operation is supported, this RFC only deals with AWS S3 scenarios.

The API is navigable over HTTP with a small number of resource types and supported HTTP verbs. All data sent or returned is in JSON-LD format. A JSON-LD Context Document will be provided later.

## Authentication

The API implements a standard OAuth2 [Client Credentials Flow](https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/) for machine-to-machine access, with [Refresh Tokens](https://www.oauth.com/oauth2-servers/access-tokens/refreshing-access-tokens/) to ensure that access tokens are short lived and can be revoked.

Throughout this example we will use the host name uol.digirati.io in examples. 

## Resources

As mentioned in [RFC 001](001-what-is-stored-in-fedora.md) we expose three main resource types:


### 📁 Basic Container

For representing structure: directories, for organising the repository itself, and for representing directories within an archival group. These are represented in JSON as:

```
{
   "type": "Container"
}
```


### 📦 Archival Group

For representing digital objects – e.g., the files that comprise a digitised book, or a manuscript, or a born digital item. An Archival Group might only have one file, or may contain hundreds of files and directories (e.g., digitised images and METS.xml). An Archival Group is the unit of versioning in the Storage API.

```
{
   "type": "ArchivalGroup"
}
```

### 📄 Binary

For representing a file, any kind of file stored in the repository.

```
{
   "type": "Binary"
}
```

## The Repository

The root of the Repository is at the path `https://uol.digirati.io/api/repository/`. The root resource is a `Container` but has the special `type` value `"RepositoryRoot"`:

```
{
  "@id": "https://uol.digirati.io/api/repository/",
  "type": "RepositoryRoot",
  "id": "https://uol.digirati.io/fcrepo/rest/",
  "objectPath": "",
  "created": "2024-03-11T12:13:22.656708Z",
  "lastModified": "2024-03-11T12:13:22.656708Z",
  "containers": [],
  "binaries": []
}
```

All containers, whether they are the root, outside of an ArchivalGroup, or inside an ArchivalGroup, have the child list properties `containers` and `binaries`. 

We begin with exploring the resources that you can see by following links in the API - i.e., browsing.

## Common Properties

### @id 

The URI of the resource in the Storage API; the unique identifier. For any resource with this property, its value is _de-referenceable_. The path part of the URI is restricted to a limited set of preservation-safe characters, see [].

### @partOf

The URI of the ArchivalGroup that the resource is in. If the resource is a Container outside of an ArchivalGroup, the value is null.

### id 

The URI of the resource within the underlying Preservation system (Fedora). This is provided for diagnostic information, callers to the Storage API will typically not have access to Fedora directly.  

### partOf

The URI of the resource's ArchivalGroup within the underlying Preservation system (Fedora). If the resource is a Container outside of an ArchivalGroup, the value is null.

### type

One of `RespositoryRoot`, `Container`, `ArchivalGroup`, `Binary`.

### origin

A URI (file system or S3) where this resource can be found in the underlying Preservation store (i.e., Fedora - for now). For a binary, this will be a file URI or S3 key. This is used by privileged systems that have permissions to read from the underlying preservation storage. Most API callers will not have this permission, and can use _exports_ to request files.

### name

A string holding the name of the resource. The expected use of this is to store the original name of the file or directory, to preserve strings that are not valid for Storage API URIs.

### created

ISO 6801 DateTime string representing the creation date of the container or binary within the Preservation system (not its original external creation date).

### createdBy

User of the storage API who created this resource.

### lastModified

ISO 6801 DateTime string representing the last modified date of the container or binary within the Preservation system (not its original external last modified date).

### lastModifiedBy

User of the storage API who last modified this resource.


# Container properties






The `containers` property lists child containers.
```
{
  "@id": "https://uol.digirati.io/api/repository/Leeds",
  "type": "Container",
  "name": "Leeds",
  "id": "https://uol.digirati.io/fcrepo/rest/Leeds",
  "objectPath": "Leeds",
  "created": "2024-03-14T14:10:15.786026Z",
  "createdBy": "leedsadmin",
  "lastModified": "2024-03-14T14:10:15.786026Z",
  "lastModifiedBy": "leedsadmin",
  "containers": [...], // 
  "binaries": []
}
```

The Repository Root, at `https://uol.digirati.io/api/repository/`, 


### A Simple Archival Group

```
{
  "@id": "https://uol.digirati.io/api/repository/Leeds/big-book",
  "type": "ArchivalGroup",
  "version": {
    "mementoTimestamp": "20240314145858",
    "mementoDateTime": "2024-03-14T14:58:58",
    "ocflVersion": "v1"
  },
  "versions": [
    {
      "mementoTimestamp": "20240314145858",
      "mementoDateTime": "2024-03-14T14:58:58",
      "ocflVersion": "v1"
    }
  ],
  "origin": "667/f65/777/667f65777927b89d3a5ec5f99246dc1dce667e2ff757a75f6df33d10cab12469",
  "name": "Big Book",
  "id": "https://uol.digirati.io/fcrepo/rest/Leeds/big-book",
  "objectPath": "Leeds/big-book",
  "created": "2024-03-14T14:58:46.102335Z",
  "createdBy": "leedsadmin",
  "lastModified": "2024-03-14T14:58:46.134917Z",
  "lastModifiedBy": "leedsadmin",
  "containers": [
    {
      "@id": "https://uol.digirati.io/api/repository/Leeds/big-book/objects",
      "type": "Container",
      "name": "objects",
      "id": "https://uol.digirati.io/fcrepo/rest/Leeds/big-book/objects",
      "objectPath": "Leeds/big-book/objects",
      "created": "2024-03-14T14:58:46.205789Z",
      "createdBy": "leedsadmin",
      "lastModified": "2024-03-14T14:58:46.205789Z",
      "lastModifiedBy": "leedsadmin",
      "containers": [],
      "binaries": [
        {
          "@id": "https://uol.digirati.io/api/repository/Leeds/big-book/objects/372705_015.jpg",
          "type": "Binary",
          "origin": "s3://uol-expts-fedora-650/667/f65/777/667f65777927b89d3a5ec5f99246dc1dce667e2ff757a75f6df33d10cab12469/v1/content/objects/372705_015.jpg",
          "name": "372705_015.jpg",
          "id": "https://uol.digirati.io/fcrepo/rest/Leeds/big-book/objects/372705_015.jpg",
          "objectPath": "Leeds/big-book/objects/372705_015.jpg",
          "created": "2024-03-14T14:58:55.938611Z",
          "createdBy": "leedsadmin",
          "lastModified": "2024-03-14T14:58:55.938611Z",
          "lastModifiedBy": "leedsadmin",
          "filename": "372705_015.jpg",
          "contentType": "image/jpeg",
          "size": 13983458,
          "digest": "b215e30cba61f42474ff5b7b3ec19e546bee6534d82ba87aed78c291d0e798e5"
        }
      ]
    }
  ],
  "binaries": [
    {
      "@id": "https://uol.digirati.io/api/repository/Leeds/big-book/10315.METS.xml",
      "type": "Binary",
      "origin": "s3://uol-expts-fedora-650/667/f65/777/667f65777927b89d3a5ec5f99246dc1dce667e2ff757a75f6df33d10cab12469/v1/content/10315.METS.xml",
      "name": "10315.METS.xml",
      "id": "https://uol.digirati.io/fcrepo/rest/Leeds/big-book/10315.METS.xml",
      "objectPath": "Leeds/big-book/10315.METS.xml",
      "created": "2024-03-14T14:58:46.396859Z",
      "createdBy": "leedsadmin",
      "lastModified": "2024-03-14T14:58:46.396859Z",
      "lastModifiedBy": "leedsadmin",
      "filename": "10315.METS.xml",
      "contentType": "text/xml",
      "size": 151449,
      "digest": "fa98850720979436375f1e7a315b60e0f38747ea4d0d439f9d9a82c8e55459d2"
    }
  ],
  "storageMap": {
    "version": {
      "mementoTimestamp": "20240314145858",
      "mementoDateTime": "2024-03-14T14:58:58.335521Z",
      "ocflVersion": "v1"
    },
    "storageType": "S3",
    "root": "uol-expts-fedora-650",
    "objectPath": "667/f65/777/667f65777927b89d3a5ec5f99246dc1dce667e2ff757a75f6df33d10cab12469",
    "files": {
      "objects/372705_015.jpg": {
        "hash": "b215e30cba61f42474ff5b7b3ec19e546bee6534d82ba87aed78c291d0e798e5",
        "fullPath": "v1/content/objects/372705_015.jpg"
      },
      "10315.METS.xml": {
        "hash": "fa98850720979436375f1e7a315b60e0f38747ea4d0d439f9d9a82c8e55459d2",
        "fullPath": "v1/content/10315.METS.xml"
      }
    },
    "hashes": {
      "b215e30cba61f42474ff5b7b3ec19e546bee6534d82ba87aed78c291d0e798e5": "v1/content/objects/372705_015.jpg",
      "fa98850720979436375f1e7a315b60e0f38747ea4d0d439f9d9a82c8e55459d2": "v1/content/10315.METS.xml"
    },
    "headVersion": {
      "mementoTimestamp": "20240314145858",
      "mementoDateTime": "2024-03-14T14:58:58.335521Z",
      "ocflVersion": "v1"
    },
    "allVersions": [
      {
        "mementoTimestamp": "20240314145858",
        "mementoDateTime": "2024-03-14T14:58:58.335521Z",
        "ocflVersion": "v1"
      }
    ],
    "archivalGroup": "https://uol.digirati.io/fcrepo/rest/Leeds/big-book"
  }
}
```


