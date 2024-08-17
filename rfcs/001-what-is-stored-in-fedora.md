# Determine best practices for *what* we store in Fedora

(This RFC is Reference M01 in Statement of Work 3)

What is the "digital preservation system"? Is that Fedora?

Fedora is the **storage** part of Digital Preservation.

A Digital Preservation System also includes the APIs, user interfaces and workflows implemented in software that _result in_ content being preserved in storage. These are other software artifacts and processing behaviours that encapsulate policy.

A Digital Preservation System is also an agreed approach to describing the content being stored, so that it can be understood later. These descriptions are not semantic (that's the catalogue's job), they are technical and structural. There needs to be a *model* (or multiple models) to describe what is preserved, and attach technical and structural information to.

A Digital Preservation System implements Leeds' [Digital Preservation Policy](https://library.leeds.ac.uk/downloads/download/178/digital_preservation_policy).

What is NOT part of Digital Preservation?

- The asset delivery - IIIF image services derived from preserved content, transcoded AV (but see below about format migration)
- The [IIIF Presentation](https://iiif.io/api/presentation/3.0/) layer
- The Catalogue API 
- Public facing web sites

The Digital Preservation System is much wider than Fedora - but it is still not the whole of the DLIP project. Fedora is part of Digital Preservation, and Digital Preservation is part of DLIP.

## Choice of Fedora

From the Fedora 6 documentation:

> Fedora is a standards-based, open source repository designed for the robust preservation of digital content.  It provides a REST interface based on web standards including the  Linked-Data Platform (LDP),  Web Access Control (Solid/WebAC),  Memento, and Activity Streams 2.0 specifications.   Persistent content is stored on disk using the Oxford Common Filesystem Layout (OCFL), the gold-standard of application-independent, transparent, and robust file storage. 

We choose Fedora because of its [Oxford Common Filesystem Layout (OCFL)](https://ocfl.io/) support. It is the Oxford Common File Layout we are interested in.

### What is OCFL?

From the OCFL site:

> [The] Oxford Common File Layout (OCFL) specification describes an application-independent approach to the storage of digital information in a structured, transparent, and predictable manner. It is designed to promote long-term object management best practices within digital repositories.
>
> Specifically, the benefits of the OCFL include:
>
> * Completeness, so that a repository can be rebuilt from the files it stores
> * Parsability, both by humans and machines, to ensure content can be understood in the absence of original software
> * Robustness against errors, corruption, and migration between storage technologies
> * Versioning, so repositories can make changes to objects allowing their history to persist
> * Storage diversity, to ensure content can be stored on diverse storage infrastructures including conventional filesystems and cloud object stores

An example _versioned_ OCFL object is laid out like this:

```
[object root]
    ├── 0=ocfl_object_1.1
    ├── inventory.json
    ├── inventory.json.sha512
    ├── v1
    │   ├── inventory.json
    │   ├── inventory.json.sha512
    │   └── content
    │       ├── empty.txt
    │       ├── foo
    │       │   └── bar.xml
    │       └── image.tiff
    ├── v2
    │   ├── inventory.json
    │   ├── inventory.json.sha512
    │   └── content
    │       └── foo
    │           └── bar.xml
    └── v3
        ├── inventory.json
        └── inventory.json.sha512
```

> "As a result of forward-delta versioning, the object tree above shows only new content added in each version."

### Fedora as a means to OCFL

The other aspects of Fedora - its "REST interface based on web standards including the  Linked-Data Platform (LDP),  Web Access Control (Solid/WebAC),  Memento, and Activity Streams 2.0 specifications" - are _means to an end_, with the end being the preservation of digital objects in an OCFL arrangement.

For DLIP we will use these means to store content; but we entertain the possibility that in future there will be other ways of getting content into preservation storage as OCFL other than via Fedora's APIs. 

**The OCFL-ness of Fedora 6 is more important to us than the Fedora-ness.**

Given this constraint, we need clear guidelines on _how_ we use Fedora; which features should we take advantage of, and what should we avoid doing? We introduce a particular implementation dependency on Fedora by relying on its APIs to get content into preservation storage, but how enduring is that dependency? 

We constrain our use of Fedora to comply with our aims by building a **_Storage API_** and insisting that no parts of the DLIP other than this API have access to Fedora's own APIs. Every interaction with Fedora must go through our Storage API layer.

The [Storage API](002-storage-api.md) may use other mechanisms than Fedora to get content into an OCFL repository. However we shouldn't abstract so far away from Fedora that we cease to take advantage of what it can do. This RFC attempts to find the balance.


## Constraints provided by a Storage API

We limit our use of Fedora resource concepts to just three of its [classes](https://wiki.lyrasis.org/display/FEDORA6x/Container+Types):

---

### 📁 Basic Container

For representing structure: directories, for organising the repository itself, and for representing directories within an archival group.

### 📦 Archival Group

For representing digital objects – e.g., the files that comprise a digitised book, or a manuscript, or a born digital item. An Archival Group might only have one file, or may contain hundreds of files and directories (e.g., digitised images and METS.xml)

### 📄 Binary

For representing a file, any kind of file stored in the repository.

---

Fedora's Archival Group corresponds to an OCFL object

Using these classes, the API enforces these rules:

* The Storage API will prevent creating a 📁 Basic Container within an 📦 Archival Group outside of versioning the Archival Group as a whole.
* The Storage API will prevent creating an 📦 Archival Group within an 📦 Archival Group (even though Fedora allows this). As an Archival group corresponds to an OCFL object, having hierarchical objects adds complexity. That modelling complexity should live in the systems that are using Fedora for Preservation, not in Fedora itself; if some larger-scale intellectual object is hierarchical, it can make more than one Archival Groups and therefore OCFL objects. 
* The Storage API will not allow direct creation of a 📄 Binary at all, they must come in as versioned updates of the whole Archival Group / OCFL object.
* The Storage API assumes that the file and folder names have been normalised to a reduced character set, still to be defined, that is guaranteed safe for S3 as well as any common filesystem or HTTP request path. 
* This means that original file names, e.g., `my document.doc` (which contains a space), need to be recorded some other way. 
* It is the responsibility of client applications like Goobi, or the deposit service, or a custom EPrints migrator, to ensure that they have already normalised filenames, and take steps to record the original file name - typically in METS - for example in the title attribute of file XML elements. See below for the suggestion that _optionally_ original file names can be recorded in Fedora in the `dc:title` property.

## Modelling

Fedora provides the [ability to model content](https://wiki.lyrasis.org/display/FEDORA6x/Data+Modeling). We could adopt techniques like the [Portland Common Data Model](https://wiki.lyrasis.org/display/FEDORA6x/LDP-PCDM-F4+In+Action) or [invent our own models](https://wiki.lyrasis.org/display/FEDORA6x/Example+Content+Model) to suit the content.

**We shouldn't use Fedora like this.**

We should be bound by the constraints above, and _carry the model as part of the preserved object_ - for example, by describing the object with a METS file.

METS is a well-established standard designed specifically for this purpose, it is safe to use it to encode and convey technical and structural metadata about digital objects, and store it alongside the content, in the preservation system, as part of the preserved object. A structural convention ensures the METS file itself is never mistaken for being part of the preserved object. For example, the root of an object contains the METS file and an `/objects/` folder and the actual content is only in that objects folder.

How an object is modelled becomes a policy decision - which can be strictly enforced, e.g., by Goobi in software as it creates a METS file - but is independent of the **storage** layer.

Different types of content can have different approaches to modelling, suited to their needs. New approaches in the future can use the existing storage API, because the model is just part of the content.

## So, what _is_ stored in Fedora?

In the Cambridge Digital Library implementation, anti-virus reports per-file and [PRONOM file format information](https://www.nationalarchives.gov.uk/PRONOM/) (maintained by the National Archives) are stored in Fedora, alongside the binary object, as additional data for each file. This means that their digital preservation has no knowledge of or dependency on METS (although it may be preserving METS files as part of digital objects).

An alternative would be to use METS files to carry this information – either a METS file generated by a pipeline during preservation, or by adding to an existing METS file generated at a previous step. It is standard practice to store this in a METS TechMD section (Goobi and Archivematica both do this).

This doesn’t make the Storage API itself dependent on METS – you can put any object in it, with or without a METS file – but if you ask it to run (for example) a pipeline that _uses_ the storage service, and that pipeline stores PRONOM and virus scan outputs, it will store it in a METS file rather than as Fedora triples.

This latter approach is in line with the idea that the Storage itself has no special understanding of what’s in it; external applications bring meaning to it, often (but not exclusively) by using METS to describe structure, administrative and technical metadata, access conditions, rights and so on as simply or as complex as they need.

### Two possible exceptions

While no additional information **at all** is _required_ to be stored in Fedora, it’s probably useful to use two existing Fedora properties that are fairly fundamental – `Name` (dc:title) to record the original file or folder name, and `content-type` to record the content type (e.g., image/tiff, application/msword). Fedora has specific API support for these, rather than being arbitrary data.

This means a preserved digital object is free to use METS – or some other mechanism – to carry whatever information it needs, including content type and original file name, but our storage API will attempt to write these two pieces of information to Fedora.

### Special additional RDF type assigned to Archival Groups

To create an Archival Group in Fedora, you [create a Container](https://wiki.lyrasis.org/display/FEDORA6x/RESTful+HTTP+API+-+Containers) but add an additional LINK HTTP Header to the PUT or POST:

> With a `rel="type"` and a URI of `http://fedora.info/definitions/v4/repository#ArchivalGroup` the client may create an Archival Group container.

Similarly, the only way you can tell a Container is an Archival Group is the presence of this header in the response.

```
Link: <http://fedora.info/definitions/v4/repository#ArchivalGroup>; rel="type"
```

The problem with this is that if you get a "directory listing" - i.e., query for child objects of a Fedora container and specify you want details back not just URLs - even with the details, you can't tell the difference between regular Containers and Archival Groups. You'd have to interrogate each one individually, which will be very inefficient for application interaction.

We need something which will appear in the aggregate details when obtaining child items of a Container - metadata that would appear for all 50 items in a list of child objects, for example. The RDF `type` of a resource is one such piece of metadata. So, when we create an Archival Group we also assign an extra `type`:

```
http://purl.org/dc/dcmitype/Collection
```

A Fedora resource usually has multiple types, and the presence of this value in the list of types tells us that it's an Archival Resource.

## Assessing this approach against JISC Core Requirements

The remainder of this document uses the "core requirements identified by UK universities for digital preservation systems providers" mentioned in this slide by Karen Colbron at Jisc as a useful reference checklist:

![core requirements identified by UK universities for digital preservation systems providers](img/jisc-uk-uni-preservation-musts.jpg)

Source: https://twitter.com/wisealic/status/1760281050490552398

The following section repeats the MUST requirements from the slide, and aims to show how DLIP as a whole meets the requirements, and how that is distinct from Fedora meeting the requirements.

For discussion: does the Leeds team agree with this list as a comprehensive indicator?

### Integrity and authenticity of the digital content

#### The system must record checksums for every file ingested
#### The system must be able to validate checksums against those supplied (if they're supplied)

These two requirements are met by Fedora itself; it can store multiple checksums and checking supplied _digest_ headers is part of a content transaction. We mediate this by the Storage API.

#### The system must generate/store checksums (or use similar integrity checking) for content supplied without checksums
#### The system must generate/store checksums (or use similar integrity checking) for content created within the system

The Preservation aspect of DLIP must ensure that content cannot arrive at Fedora without a checksum that Fedora can verify once the file is "at rest" - safely preserved.

That means that _something_ has to generate a checksum higher up the chain. But this will vary depending on the content. For content introduced as files uploaded to a web user interface, that checksum should happen on the client (in the browser), be verified at the server, and travel with the content until it is safely stored. For other workflows the point at which a checksum is generated will vary.  While the storage API should always require a checksum, different pipelines into that storage can generate checksums at appropriate points.

#### The system must support periodic integrity checking, reporting any damaged or missing files

Fedora supports [fixity checking](https://wiki.lyrasis.org/display/FEDORA6x/RESTful+HTTP+API+-+Fixity) - but the orchestration of periodic large-scale checking of the preserved content would need to be organised higher up, as some other process within DLIP.

There is a balance between checking too often (it uses compute resources to perform checks) and checking not often enough (a problem goes undetected for years). Outside of this document, a policy needs to be specified for:

* How to check for mismtached checksums
* Whether it's possible to use underlying features of AWS to do this more efficiently (a checksum can be stored in AWS metadata, but does Fedora do this when backed by S3?)
* How often to run these checks
* What happens when a problem is detected? We intend to store copies in at least two other geographic locations; what's the process for fixing a detected problem?

#### The system must be able to generate an audit log and record event metadata describing all enabled actions

Some actions will be calls to the Fedora API, and some will be in consuming APIs or pipelines. We can consolidate these into a single _stream_ of preservation activity.

Fedora provides an [Authentication and Authorization Framework](https://wiki.lyrasis.org/display/FEDORA6x/Authentication+and+Authorization).

We should map human and machine users of the Preservation System to Fedora users, so that the actor responsible for an action is recorded directly in Fedora. However, we may not want to use Fedora's own _Authorization_ mechanisms. The only caller of Fedora will be the wrapper storage API, and this in turn will be called by various applications higher up the chain. It's better that they manage their own authorization, to avoid having authorization business rules within Fedora itself (which is just our OCFL gateway).

We will still need to create Fedora users and map them to identities in other systems.


### Data model

#### The data model must be able to capture digital objects that are composed of multiple hierarchical components

This is where we explicitly say that we don't do this _formally_ at the Fedora level, even though it allows it. Ultimately the preserved content is a set of OCFL objects within a containment structure (folders), and we won't allow one OCFL object inside another because we won't allow an Archival Group to exist within another Archival Group.

Modelling decisions external to Fedora determine what an Archival Group _means_. And one influence on that is what it would mean to _version_ an object.

Examples:

* A book may have internal structure - chapters - but still be considered a single Archival Object. The structural model is captured in METS structMap elements (and will later be directly reflected in IIIF Ranges).
* A Periodical may comprise hundreds of _issues_ within dozens of _volumes_. You could choose to model each issue as a separate object, or each volume, or even (unlikely) the whole publication history of the periodical. All could in theory be expressed as a model in (large) METS files. Modelling should be guided by making manageable sized digital objects on the one hand, and future recoverability as a sensible intellectual object on the other. What would it mean to version an issue of a periodical (e.g., to insert a missing scanned image)?
* An archival hierarchy _probably_ translates to distinct versioned preserved digital objects at the **item** level - but not necessarily.
* Access control information - the _access conditions_ specified for individual files, or sections - may be carried by METS files as administrative metadata. A tool like Goobi allows specification of access conditions at arbitrary levels as part of the workflow - e.g., one file may have a restricted access condition amongst otherwise open content, or a particular sequence of images - a particular letter in a group - may be given a distinct access condition. It is not for Fedora to assign any meaning to this; meaning is inferred by the asset delivery part of DLIP, which understands the access conditions pertaining to a particular file, and can match them to roles (permissions) claimed by authenticated users.

In short - the Preservation aspect of DLIP must allow us to model and preserve "digital objects that are composed of multiple hierarchical components" but it is not _necessarily_ within Fedora that the relationship between parts is captured.

#### Digital objects must be assigned unique identifiers

Everything in Fedora must have a unique URI, but the source of path elements in the URI will in DLIP be external to Fedora - on no account should we ever leave Fedora to assign a GUID because we have failed to specify our own identifier. 

The source of identity is the [identity service](https://github.com/uol-dlip/identifier-service)

### Exit strategy

#### The system must be able to export or copy digital content and all associated metadata in a manageable format/structure for ingest into another system

This format/structure is OCFL _plus_ whatever additional files are capturing the model within an object (typically METS). We don't even need Fedora to export, we can just take the OCFL object from the underlying storage, with all its version history plain to see.

**_In fact this is a design principle - we must be able to do this independently of Fedora_**

This exit strategy is also far-future access to the content in the absence of the technology it today depends on. An OCFL repository should include a copy of the OCFL specification at the root; we should likewise include copies of other relevant specifications that are required to interpret the content (for example the METS specification).

### Ingest

#### The system must enable the ingest of digital content and associated metadata
#### The system must be able to keep the original bitstream
#### The system must be able to provide reports on the success/failure of ingest activities

These three are all core aspects of Fedora itself, and we will expose them to dashboard/admin applications via the Storage API. The "original bitstream" is assumed to mean the file to be preserved, i.e., the system is not just making access copies and discarding the original. 

What defines the original bitstream is a policy decision, however. For example, a manuscript digitisation activity may capture camera RAW files, but decide NOT to preserve these after processing, and only preserve TIFFs or JPEG 2000.

### Characterising ingested digital (?)

#### The system must identify known file formats and reference registries of further information

This won't happen in Fedora. It will be the responsibility of **pipelines** higher up to run tools that identify what PRONOM file type a file has; this PRONOM identifier references the PRONOM registry. The PRONOM identifier will usually be stored in Fedora within a METS file for the digital object. We will also store the content type (aka media type aka mime type), where known, as a field in Fedora itself _as well as in the METS file_.

The significance of the content type is often downplayed and while the PRONOM identification is crucial, the fact that the content will be provided over the web means we should where possible record our best understanding of the content type as well.

Part of the overall system design is to specify **pipelines** that produce metadata, such as virus checking and file format identification. How these are invoked is still to be designed.

### Replication and storage management

#### The system must have the ability to store multiple copies of digital content (potentially on different systems and different locations)

OCFL makes this easier for us; it is sufficient to copy the OCFL object to another file system or blob storage anywhere in the world. This is orchestrated outside of Fedora and a Fedora instance has no knowledge of other locations for the content it holds.

We can probably adopt the same approach as Cambridge and use AWS-level inventory and replication mechanisms. We anticipate storing copies in AWS Glacier in a different region, and Azure Blob Storage in a different region; this gives redundancy of both location and cloud provider.

The file name normalisation constraint mentioned above should be strict enough that all paths will be valid in any conventional file system, S3 or Azure-style blob storage.

### Preservation actions

#### The system must enable the migration of files from one format to another

_See [Preservation action](https://www.dpconline.org/handbook/organisational-activities/preservation-action) from the DPC Digital Preservation Handbook._

This is not provided by Fedora, and may not even be the concern of the Preservation System at all. All Fedora does (via the storage API and with the assistance of replicated content in other locations) is preserve what it's given to preserve.

There are two aspects to this question and they relate to the purpose of file format migration.

##### Access to the content for users

In DLIP, the IIIF Cloud Services has the job of transforming files into web-suitable formats. Most obviously, an archival tiff might be provided as a IIIF Image Service. But also, a high resolution video master may be made accessible as a web-friendly MP4. And an obsolete WordPerfect document may be made available as a PDF. But these are asset **delivery** concerns rather than preservation concerns. Some of them are runtime transformations, on demand. And they have nothing to do with whether the original format is obsolete, they are about transformations for access via the web. 

In an ideal world, you always have some software that can read the original, even if many users benefit from a derivative whose format may change over time to suit contemporary tools.

##### Safety of the intellectual content in the face of obsolete software 

The preservation concern is "what if we lose the means to transform the WordPerfect document to a PDF, or even open the WordPerfect document anywhere?" 

While we can prioritise open formats for access, we can't change the original format, which may be closed or proprietary. Open format derivatives are our way of maintaining access to the original intellectual content.

Even if _transformation_ of content may lie outside the preservation storage, we might still want the ability to put transformed versions of originals back into preservation storage (e.g., so that the more accessible PDF version is also safe and not dependent on runtime infrastructure).

We could for example update a preserved object with a new folder of derivatives next to the original container structure, if we are concerned that the formats are going to become inaccessible. The originals must always be preserved and not intermingled with derivatives, but we might choose to occasionally enlarge the preserved object with a shadow subset of transformed files in parallel. And it could be the IIIF Cloud Services that makes these derivatives.

The digital preservation concern is doing any "format migration" in good time, before the ability to do so is lost. But regular incremental migration of formats from one version of software to another may be wasteful of resources and unnecessary. It may be that additional access formats are created early on in likely very durable formats (e.g., a PDF and a plaintext version) and not revisited. A digital object could be preserved in its original state and be accompanied by an ingest-time (or soon after ingest-time) set of files in trusted long term formats. This would be driven by external pipelines, probably by IIIF Cloud Services (IIIF-C). IIIF-C can make a derivative for web use, and keep it, but that is not the same as preserving it - that would mean adding it to Fedora.

A related question is derivatives like OCR or human-generated transcription - these might only be generated after the object is preserved, but still be worth preserving - putting back into the object, enriching the object.

In either case we are constructing additional workflows to take a subset of what the IIIF-C can produce for an asset, and putting it "back" into the original digital object.

_This interpretation of meeting the format migration requirement needs to be discussed._

#### The system must record preservation actions (and outcomes) in the associated metadata

Any files "introduced" to a digital object in preservation storage in the way described above need a clear audit trail of what happened. This parallel structure of derivatives needs to be transparently comprehensible to anyone making sense of the preserved content in the future.


### Management of digital content and metadata

The following will all require a user management layer on the Storage API that is running above Fedora. This will use OAuth2 to protect API operations, with different roles with different permissions.

The issuing of API tokens to applications with roles, or applications acting on behalf of users with roles, still needs to be designed; we assume that the source of user identity is the University's Identity Service.

#### The system must provide controls to minimise the risk of accidental/malicious deletion or content change

It's actually quite hard to completely remove content from Fedora, and previous OCFL versions will be preserved. But sometimes you have to remove things completely. The Storage API needs to rely on permissions - actors invoking the API, whether impersonating a user or as systems, may have different abilities to perform certain actions.

We may _also_ want the ability to base permissions on _where_ in the repository a user/actor is allowed to perform an action. Assuming that a logical structure for content is created, a user may be allowed to preserve objects under /aaa/bbb but not under /aaa/ccc. This might be too much complication though.

This could also be done with different instances of Fedora with different permissions.

#### The system must be able to ingest and manage all required metadata including metadata appropriate for specific content types

The key here is "and manage" - Fedora is not aware of what the content means, including metadata such as a METS file - but other parts of the DLIP are.

#### The system must enable the managed disposal of content

A takedown or copyright request may require the complete removal of content down to the OCFL level. A whole OCFL object may be reasonably straightforward to remove, but it is far more complicated to remove a file within an OCFL object _and all its version history_.

This is a very rare event. Usually the action would be to change the access conditions on an individual file, or group of files, which is a matter of editing metadata and creating a new version. The upstream asset delivery services would change access according to the changed policy.

#### The system must restrict any actions to manage digital content to those with authorised user login and/or user roles

(see above)

### Discovery

These two sections build on access control established above.

#### The system must ensure that all digital content and associated metadata is only discoverable by authorised users

#### The system must ensure that all digital content and any associated metadata is only accessible by authorised users


### Training, support and help

These two sections can form part of Digirati's support arrangements.

#### The system supplier must provide training for system users

#### The system supplier must provide a support mechanism for system users

