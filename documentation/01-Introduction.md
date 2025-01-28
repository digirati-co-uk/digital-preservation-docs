# Introduction

(diagram here, summarised below - the Preservation stack)

```
    OCFL (in S3)     - direct origin access to (very) trusted readers
                       replication to other locations


    Fedora           - (not accessed by ANYTHING except Storage API)


    Storage API      - Read by IIIF Builder, may be used for non-standard Preservation tasks
                       Does not know what a METS file is (it's just another binary)
                       Updates ArchivalGroups via Import Jobs that point at file locations


    Preservation API - Used by Goobi, Preservation UI, and most ad hoc scripts
                     - Uses METS as model for object
                     - Offers Deposits to provide working area for new ingests
                     - Manages (reads and writes) METS files where it is in charge
                     - Reads METS files from other applications (Goobi, and possibly Archivematica)
                     - Manages invocation of pipelines to embellish managed METS files with additional information
                     - Process external packages (eg BagIt) into Deposits and METS


    Preservation UI  - Used by humans (staff and external contributors)
                     - Browse the Digital Repository
                     - Create new deposits and work on them
                     - Upload files
                     - Trigger pipelines

```

## OCFL

The [Oxford Common File Layout](https://ocfl.io/1.1/spec/) (OCFL) is what ends up preserved "on disk" - or in our case, in AWS S3. OCFL is the goal of the rest of the digital preservation stack. Versioned archival objects, in a file layout that conforms to an agreed specification.

The idea is that we can recover everything that was preserved just from a backup of the OCFL file system (or S3). For example, we find a hard drive with an OCFL file layout and a copy of the OCFL specification.

<img src="images/Hard_Drive.webp" alt="Hard Drive" width="200"/>

We don't need running systems just for there to be preserved content.

The individual units of Preservation - the things we consider to have boundaries that sensibly define versions - correspond to [OCFL objects](https://ocfl.io/1.1/spec/#object-spec). An object might have one file or might have hundreds. It might correspond to a digitised archival _Item_, a digitised book, or a born digital _Item_. 


## Fedora

**Fedora is a Gateway to OCFL**

We could write the OCFL directly to disk or S3, managing it ourselves. But we don't do that, because [Fedora 6](https://wiki.lyrasis.org/display/FEDORA6x) does this for us. OCFL is how Fedora 6 persists the repository to disk, and how it manages versions.

Fedora 6 offers many modelling and management features; its implementation of the Linked Data Platform and ability to store arbitrary triples allows it to be used to model complex objects within the repository.

_We choose not to make use of these features_. We are using Fedora as the means of writing OCFL. 

For this reason, we only use a subset of Fedora's capabilities.

 - Basic Containers (which we everywhere just call Containers)
 - Binaries
 - Archival Groups (which correspond to versioned OCFL Objects)
 - Transactions


## Storage API

All communication with Fedora is via the Storage API. Nothing else can talk to Fedora!

Async processing of import job

Manages transactions, validation

Allows retrieval of containers and archival groups

By listing container.binaries with their origins, allows trusted callers to learn the direct location on disk

(stream of content?)

The Storage API can store anything you can describe in an Import Job, as long as it has access to the origin locations of the binaries

All it needs in an import job are 

- URIs of source and destination
- SHA256 hash (digest) of each binary
- Name (records non-URI-safe original file and directory names, e.g., "my notes.doc")
- Content Type of binaries

It offers no modelling capabilities other than the file system layout.

Direct use of the Storage API is rare, as most use cases are better served by the Preservation API

## Preservation API

The Preservation API
Role of METS
Uses METS to model digital objects

(later) Manage logical structure

## Preservation UI

Browse the repository

Work on a deposit
A combined view of METS (what is in the Archival Group) and Deposit (what is in the working area)


## IIIF Builder

Understands the extra things that Leeds users are putting in the METS files


## IIIF Cloud Services

Hosts and manages the IIIF Resources built by IIIF Builder, and the Content Resources generated from source binaries in digital preservation (most commonly, IIIF Image API services from archival TIFFs).