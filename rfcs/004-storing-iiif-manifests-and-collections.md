# Storing IIIF Presentation API resources

## Introduction

A key element of Leeds' DLIP is the production and serving of **IIIF Manifests**, and related IIIF API resources such as **Collections** and **Annotation Pages**, as well as resources derived from IIIF Assets and Manifests through machine- and human-driven processes (OCR, transcription, tagging, image analysis, entity recognition) - referred to as _adjuncts_ in this RFC.

At first, all of those IIIF Manifests will be representations of digital objects stored in Fedora (digital preservation repository), and will be produced by an entirely automated process from earlier workflow on the objects in Goobi (for digitised items) and in the to-be-built DLIP Preservation UI / Deposit Service (for, mostly, born digital items).

Later on, there are likely to also be Manifests produced all or in part _manually_ - for exhibitions, for storytelling, for driving web user experiences in addition to rendering items. Manifests might also be created for teaching purposes. A Manifest might be assembled from scratch, or might be derived from an existing, automated Manifest. Manifests might combine images and other assets from different IIIF sources. 

We don't want to be too prescriptive at this stage, but it is clear that a flexible "IIIF Platform" is a crucial part of the DLIP strategy, a key enabler of a wide variety of features and services powered by IIIF, as described in the original Technical Discovery work. The platform needs to do all it can to help applications _build_ IIIF Presentation API resources, and to safely serve them at scale. It also needs to act as a IIIF Presentation API Repository, to store arbitrary IIIF Manifests, Collections and possibly other resources arising across the Library's activities, and serve that IIIF to the public, or restricted groups.


### Is IIIF-CS this platform?

_Partly._ Digirati's IIIF Cloud Services Platform (developed for Wellcome and referred to by them as the _DLCS_) is _asset centric_ - give it an image, it will provide a IIIF Image API endpoint for it. Give it a video, it will provide web-friendly transcodes. Give it a PDF or in fact any file, and it will serve it - all of these services protected by the interoperable IIIF Authorization Flow API, integrated with your _Identity Provider_.

It does much more than this - its API allows _management_ of those assets, assignment of arbitrary metadata to those assets, and projection of asset sequences into IIIF Manifests, Zip files and PDFs. An example of this was given in the Storage API demo, where the contents of a Fedora Archival Group were registered with the IIIF-CS platform, and used to generate a IIIF Manifest.

But it doesn't have a notion of a IIIF Manifest (or Collection) as a resource that it is storing and serving. It uses the concept of Spaces for organising assets, but spaces are really just rows in a database table.


### Prior art

#### Named queries and Skeleton Manifests

A common pattern for use of IIIF Cloud Services is to register assets with at least two metadata fields - one to **group** a set of assets together (e.g., 37 assets all with the string metadata value "book-995"), and one to order them (e.g., those same 37 assets have an ascending integer metadata field that runs from 1 to 37). Then, use the _[Named Query](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/named-queries)_ feature to *project* those assets into what we usually refer to as a _Skeleton Manifest_ ([here's an example](https://dlcs.io/iiif-resource/wellcome/preview/5/b31477707) - this JSON is the projection of a query into IIIF-Manifest form).

Another named query technique is to say that all the assets in one Space are ordered by one of their number fields. One space per manifest.

We can then load the skeleton manifest using a IIIF library in the programming language of our choice, or load it as a plain JSON object, and _decorate_ it with the information we require (labels, metadata, rights statements etc), saving it _somewhere else_ where it becomes the published official Manifest for the item. This approach can work well for small collections, but it's not very controlled, and is one-way.


#### Wellcome's IIIF Builder

At Wellcome, Manifests and other non-asset IIIF resources are built by a very complex application [iiif-builder](https://github.com/wellcomecollection/iiif-builder). Some of it even pre-dates IIIF itself; it has been worked on since 2012 and has outlasted changes of Digital Preservation platform and sources of descriptive metadata (its first incarnation integrated with Preservica and the Sierra LMS).

* It understands both Goobi METS and Archivematica METS - sources of technical, administrative and structural metadata about digital objects
* It understands the Wellcome Storage Service - it's able to locate source assets (archival images, hi-res video, etc) from digital preservation; it can resolve an S3 **_origin_**
* It understands the Wellcome Catalogue API - a source of descriptive metadata about digital objects
* It understands the IIIF Cloud Services API and synchronises assets referenced by METS files with that API, for asset delivery as Image Services and AV derivatives 
* It seeks out METS-ALTO and other OCR files referenced in METS and builds textual representations, which then power:
  * Search Within (within a Manifest only) using the IIIF Search API
  * W3C web annotations providing a text layer to IIIF clients that understand them
  * Full text downloads
  * W3C web annotations identifying the boundaries of figures in printed books and other material
* It builds its IIIF Manifests independently of the asset delivery services, and provides them on the web ([example](https://iiif.wellcomecollection.org/presentation/b31477707))
* It understands Wellcome's Catalogue API and what it needs to use from that in the production of IIIF Collections (for archival hierarchy, multi-volume works and periodicals) and Manifests.
* It is resilient to large-scale harvesting of Manifests and text resources (e.g., by bots - an increasing problem).

Despite all these features, its treatment of IIIF Presentation API resources is entirely _derivative_ - there's no possibility of creating a IIIF Manifest externally and using iiif-builder to store it and serve it. A Manifest is always the output of programmatically transforming other data. It's powerful but inflexible, and completely tied to its sources. This is not a problem for its intended purpose and current use at Wellcome.

It has MANY features we would want to use in DLIP, but they are tied to producing IIIF in one way only. They can't be driven from outside. 

Wellcome's iiif-builder pre-dates the IIIF Cloud Services (or DLCS) and even in part pre-dates IIIF; it was necessarily bespoke and complex _before IIIF came along to give a clear dividing line between open standards and local implementation details_.

#### "Presley"

Over the years, Digirati has built several different implementations of an IIIF Presentation Server, usually with the "Presley" project code name - an environment in which IIIF Manifests can be created and enriched. With all of these, the level of granularity of storage has been a problem. Whole Manifests as JSON objects? Decomposed individual parts of the model, independently editable? 

#### Madoc

These various IIIF storage approaches are at their most developed in [Madoc](https://madoc.digirati.com/).

There are definitely many uses for Madoc in the overall DLIP vision, but it is not the IIIF Production line, the storage and serving solution at scale, for the bulk of the Collection. Madoc could however be well integrated into the solution that follows in this RFC.

#### Designing a IIIF Repository for Harvard

In 2020 Digirati performed some design and architectural work for a IIIF Presentation Store for Harvard University, including a fully developed relational database schema to store the IIIF Presentation model at scale. This was intended to sit alongside an IIIF-C-like asset delivery solution.

While this relational store would have been very flexible, it exceeded the requirements for management of Presentation API resources at the time, and was in many ways too flexible and therefore too open-ended to develop applications against.


#### Designing a IIIF Storage Protocol for Canadiana / CRKN

As a by-product of work on our Manifest Editor, we proposed a [REST protocol](https://github.com/digirati-co-uk/iiif-manifest-editor/wiki/REST-Protocol) for storing IIIF that the Manifest Editor could use, and did some experimental work, based on the API offered by CouchDB, to look at how such a protocol might behave.

 - [Examples of POST operations](https://github.com/tomcrane/iiif-repository/blob/main/ProtocolTests/PostTests.cs)
 - [Examples of PUT operations](https://github.com/tomcrane/iiif-repository/blob/main/ProtocolTests/PutTests.cs)


### Analysis of IIIF Presentation Services

Taken together, the examples above could be positioned at various points in a space with the following dimensions:

 - Granularity of backing storage - from blobs of JSON for whole Manifests, to a relational schema that captures every aspect of IIIF in multiple tables; or even a triple store.
 - Granularity of CRUD operations - can I patch in an additional image, or modify a metadata field, or am I always updating a whole Manifest? What's the unit of work?
 - Integration with asset delivery - is the IIIF Presentation store wholly independent and unaware of how image services and AV resources are actually served? Or is it able to bootstrap the creation of IIIF Presentation API resources and integrate it with asset registration? That is, is there a concept of "here is a Manifest and here are the studio TIFFs that comprise it, in the right order... please make something that will work on the web... produce a Manifest that points at IIIF Image API endpoints derived from those TIFFs"
 - Richness of additional services - from the IIIF-model-only REST protocol for the Manifest Editor, to a rich suite of _derived_ services like search within, search across, enrichment pipelines (see below), storage of adjuncts (see below) associated with or derived from assets.

At Wellcome, interactions with the IIIF-CS platform (DLCS) are about asset registration and synchronisation. Knowledge of what assets are needed for a particular Manifest, in what order, is derived from METS files and encoded in [stringN](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/asset#string1) and [numberN](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/asset#number1) fields when iiif-builder, reading those METS files, registers assets with the IIIF-CS platform. The value of those fields means nothing to IIIF-CS itself, it's iiif-builder that gives them meaning. IIIF-CS just stores the assets with this extra metadata.

This synchronisation behaviour is very powerful and useful. Abandoning this in favour of a Manifest-first approach, such as might be constructed in a manifest editor or programmatically, might be brittle or overly complicated for large scale digitisation workflows.

Can we synchronise a Manifest (the structured digital object) with its assets at the same time? Combine two very distinct activities in the current Wellcome DLCS into one logical synchronisation operation? That would be very powerful. But...

...We want to be able to store _ANY_ manifest or collection in the platform:

 - manifests where all referenced assets and adjuncts are also managed by platform
 - manifests where some are, and some are external
 - manifests where ALL are external (or _unknown_) - a purely Presentation API storage service, like the CRKN protocol, with no services provided for assets themselves. A IIIF-flavoured JSON document store.

But we also want to benefit from asset queries and Wellcome-style synchronisation of platform assets with the assets asserted in METS files. [Batches](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/batch), [queues](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/queues), and other workflow-friendly processes. It won't be good enough to add assets only through the lens of a Manifest, building the Manifests separately and storing them in a IIIF Repository.

For Leeds we want to synchronise the platform's stored manifest and its assets with the METS as a whole, with additional semantic metadata, adjuncts (see later), enhancements and derivatives. 

> As described in the Technical Architecture there will still be a need for a IIIF-Builder, but rather than it doing _everything_ as at Wellcome, it leans on the services of a much richer IIIF Platform. This richer platform, by making many of those Wellcome services more generic, serves as a foundation for Leeds to build multiple IIIF powered applications as part of DLIP and in the future.

At the moment we can't provide the same suite of services as Wellcome without re-writing them in a Leeds context - so if we are going to do this, we should do this in a way that allows multiple services to be built on top.

### What we have learned from the above

For storing IIIF Manifests that may be edited by external processes, we don't want to deconstruct and reconstruct the Manifest from some other internal representation (a relational schema, a triple store, fragments of JSON). IIIF is very flexible but also very variable; if we commit to some kind of decomposition on receipt of a IIIF payload, we add a new layer of complexity and fragility to the platform. It's a document.

* IIIF Manifests are the unit of distribution and therefore the unit of persistence; if we create a Manifest, we need to save it again whole. As long as it's valid IIIF, we can't police what goes in it.

***BUT...*** sometimes we **do** want to generate and manipulate IIIF without having to think about the whole Manifest. At its simplest, you can conceive of a Manifest as a sequence of assets - I have 20 JPEGs... turn them into a Manifest, give it a label - and I have something publishable. We need more than just a Manifest-sized JSON-blob-store when projecting a Manifest out of a series of assets, or finding out where assets are being used, or adding an asset to a manifest. There's more to storing IIIF than a generic JSON document store, and for large-scale digitisation workflows, we want the platform to assist the construction of IIIF using simple patterns. We also want to be able to query at least some aspects of a large amount of stored IIIF.

Where's the middle ground?

* A [CRKN-like protocol](https://github.com/tomcrane/iiif-repository/blob/main/ProtocolTests/PostTests.cs) for manifests, but with added asset synchronisation features.
* ...Where the Manifest can be thought of as a Container or organisational unit of an ordered sequence of assets...
* But can carry arbitrary additional information, and complex _Canvas Composition_ - Choices, multiple images, arbitrary targets.

In the current IIIF Cloud Services platform, there is no notion that assets are members of any larger set, except in two ways:

1. We can organise them into [spaces](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/space), which allow for different default policies
2. We can impose our own metadata so that we can use it to generate [named queries](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/named-queries).

We could use the existing Space resource to represent manifests (one space per manifest), but we would still need the second technique to assign ordering within the manifest. And there's still nowhere to "hang" all the additional information we want the manifest to carry. Spaces are more of an orthogonal partitioning mechanism, used for organising assets at a larger scale (e.g., Wellcome's Space 5 has 56 million assets in it).

This RFC proposes new storage concepts to be introduced to IIIF Cloud Services:

* Manifests, that can contain assets, similar to the way spaces can contain assets (in fact they use a space-per-manifest under the hood)
* Collections, that can contain Manifests or other Collections, but that come in two flavours:
  * IIIF Collections - e.g., to represent multi volume works, periodicals etc
  * Storage Collections - like folders to organise the storage of IIIF resources within the platform

Assets can be "added" to Manifests, and the platform will generate an initial IIIF Manifest from the assets within a Manifest container. 

**You can create a Manifest and then add assets into it.** But they are not just containers...

* A **IIIF Manifest** always has a stored JSON representation - a document - that can carry any information that we can model in IIIF - the JSON representation is a IIIF Presentation API 3.0 Manifest.
* A **IIIF Collection** always has a stored JSON representation.
* A **Storage Collection** may simply be a container, but the platform can express it (make available as API) as a IIIF Presentation API 3.0 Collection if you enable it to be exposed that way. We can't add arbitrary additional IIIF properties to a Storage Collection (because there is no stored JSON), but crucially it is _navigable_ by anything that understands a IIIF Collection.
* An asset can appear in multiple Manifests if required - it's not restricted to use in the Manifest it was initially put into.
* A IIIF-CS stored Manifest can reference IIIF Image API endpoints and other content resources (images, AV, etc) _that are not being provided by IIIF-CS_. An IIIF-CS stored Manifest can have all of its referenced content resources as assets registered with IIIF-CS (the standard model for Digitised and Born Digital workflows), or some of them, or even none of them. This latter scenario is like the CRKN protocol - we're only loading and saving IIIF JSON documents.
* The platform offers helper APIs to manipulate assets within a Manifest. 
* We should make it easy to write _synchronisation code_ so that a much simpler iiif-builder component can apply changes from METS files to IIIF Manifests.
* iiif-builder is just one client; IIIF Manifest Editors, exhibition builders and bespoke tools are also clients.

And from these emerge usage scenarios:

* Create a new manifest, POST new assets into it like a container, but you can see it served as a IIIF Manifest
* Fetch the Manifest, manipulate it, add arbitrary additional IIIF (e.g., label, metadata) and save it back
* Add additional assets easily without having to manipulate IIIF Presentation API model directly - "I want to add this image between canvases 3 and 4"
* (later) Associate textual content with IIIF Canvases within the Manifest
* (later) Generate Search Within services for a Manifest from that textual content
* (later) Transform that textual content into IIIF-native forms (Annotations) from other formats (e.g., ALTO, hOCR)
* (later) Transform textual content into web-native forms for innovative UI (SVG, plain text)
* (later) Generate Search services for whole Collections, and more generally across Manifests

#### IIIF Structure

A Manifest is not just a sequence of assets; a Manifest's `items` property is a sequence of Canvases, each of which has one or more Annotation Pages, each of which has one or more Annotations, of which at least one is usually an Annotation with the motivation `painting` that provides the Canvas's content. This multi-level structure is what gives IIIF its power but is complex for a user to manipulate directly. We should be able to _safely_ bypass it for simple operations - that is, don't force API consumers to navigate this structure just to add an asset to a Manifest, but don't pretend that the structure doesn't exist and prevent the use cases that need this structure.


## Implementation

Throughout the following text we will use the URL `iiif.library.leeds.ac.uk` as the root of the IIIF Cloud Services platform - the public facing accessible contents, and `api.iiif.library.leeds.ac.uk` as the endpoint for manipulating IIIF via the IIIF-CS API. If we want to create manifests, edit them, view additional properties, it's on the `api.iiif..` hostname, a JSON REST / CRUD API secured with OAuth2.

When serving IIIF Presentation API resources to users over the web, it's on the `iiif...` hostname - still serving (mostly) JSON, usually (but not always) open, without access control.

The "same" resources are available on both hosts, but the representation is much richer on the API host.

> ⚠ **IMPORTANT** See [Endpoints](020-files/api-endpoints.md) for a discussion that might change this approach and give us one endpoint only.

### Storage Collection

A Container that does not have a JSON representation. It's simply a container. We can't add IIIF `label`, `metadata` or any other fields to it. there is no JSON representation of this resource stored in S3 or anywhere else, it's entirely dynamically generated (see schema suggestion later).

`https://api.iiif.library.leeds.ac.uk/` is the root storage collection.

> ⚠ Again, see [Endpoints](020-files/api-endpoints.md) for alternative.

The API response that comes back from that endpoint is a **valid IIIF Collection**, with an additional `@context` that allows us to attach a _pager_ to our Storage Collections, and other properties (more later):

```json
{
   "@context": [
       "http://tbc.org/iiif-repository/1/context.json",
       "http://iiif.io/api/presentation/3/context.json"
   ],
   "id": "https://api.iiif.library.leeds.ac.uk/",
   "type": "Collection",
   "behavior": [ "storage-collection", "public-iiif" ],
   "label": { "en": ["(repository root)"] },
   "items": [
      {
        "id": "https://api.iiif.library.leeds.ac.uk/manuscripts/",
        "type": "Collection",
        "label": { "en": ["Manuscripts"] }
      },
      {
        "id": "https://api.iiif.library.leeds.ac.uk/archives/",
        "type": "Collection",
        "label": { "en": ["Archives"] }
      }
   ],
   "totalItems": 4,
   "view": {
      "id": "https://api.iiif.library.leeds.ac.uk/?page=1&pageSize=2",
      "@type": "PartialCollectionView",
      "next": "https://api.iiif.library.leeds.ac.uk/?page=2&pageSize=2",
      "last": "https://api.iiif.library.leeds.ac.uk/?page=2&pageSize=2",
      "page": 1,
      "pageSize": 2,
      "totalPages": 2
  },
  "seeAlso": [
    {
      "id": "https://iiif.library.leeds.ac.uk/",
      "type": "Collection",
      "label": { "en": ["(repository root)"] },
      "behavior": [ "publicVersion" ]
    }
  ],
  "created": "2024-01-01T12:00:00",
  "modified": "2024-02-01T12:00:00",
  "modifiedBy": "https://iiif.library.leeds.ac.uk/users/tom",
}
```

The `view` property is one that the [IIIF-CS API uses already](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/collections), on non-IIIF API resources - for example paging through a space. The `PartialCollectionView` is from the [Hydra hypermedia API Specification](https://www.hydra-cg.com/spec/latest/core/#collections) that the IIIF-CS Platform uses for all non-IIIF API operations.

>❓It's possible that paging will be added to IIIF Collections for IIIF 4.0 - back by popular demand. It was removed in 3.0. If so, we should use that paging mechanism and not the Hydra PartialCollectionView. The underlying implementation in IIIF-CS API won't be very different.

In the above example there are 4 items that are immediate children of `https://api.iiif.library.leeds.ac.uk/`, but requesting that resource directly only indicates two of them in the initial response. We can use the PartialCollectionView to navigate to the others, and the `totalItems` property to see how many items altogether. Here the default page size is 2 to keep the example small, it would obviously be much larger (100 or more) in the production API.

The `seeAlso` property links to the public view of this collection _if there is one_ - it's optional whether a storage collection has a public representation. You might have a "folder" with 100,000 Manifests in it; there is no need for this to appear to the public.

>❓How to govern this visibility - how do you as an API user specify the behaviour? `isStorageCollection` on Collection table, StorageCollection `behavior`

The public version (if configured to be public):

* has only the IIIF `@context`
* is not paged (no `view` or `totalItems` properties)
* does not link back to the API version
* does not have a qualifying `behavior` property.

### IIIF Collection

A Container that is also exposed as a IIIF Collection. A JSON representation of this resource is stored on disk (i.e., in S3). The platform also maintains the containment hierarchy information in its database schema. An update to the Collection resource is at the level of the Collection JSON (a PUT or a POST), and the platform needs to parse and translate the implied members and store them in the Collections table (see suggested schema below).

Here is the **public** view of a IIIF Collection within our repository:

```json
{
  "@context": "http://iiif.io/api/presentation/3/context.json",
  "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century",
  "type": "Collection",
  "label": { "en": ["14th Century Manuscripts"] },
  "metadata": [
    {
      "label": { "en": [ "Information" ] },
      "value": { "en": [ "This is additional information" ] }
    }
  ]
  "items": [
    {
      "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-125",
      "type": "Manifest",
      "label": { "en": ["MS.125"] },
      "thumbnail": [
         "...": "..."
      ] 
    },
    {
      "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-126",
      "type": "Manifest",
      "label": { "en": ["MS.126"] },
      "thumbnail": [
         "...": "..."
      ] 
    }
  ]
}
```

The API view again has the additional `@context` and pager features (`view`, `totalItems`) shown in the Storage Collection example, as well as some other fields:

```json
{
   "@context": [
       "http://tbc.org/iiif-repository/1/context.json",
       "http://iiif.io/api/presentation/3/context.json"
   ],
   "id": "https://api.iiif.library.leeds.ac.uk/iiif/collections/pbf237mc",
   "publicId": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century",
   "type": "Collection",

   "slug": "14th-century",
   "parent": "https://api.iiif.library.leeds.ac.uk/iiif/collections/ae45gh7e",
   "itemsOrder": 78,

   "label": { "en": ["14th Century Manuscripts"] },
   "items": [
    {
      "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-125",
      "type": "Manifest",
      "label": { "en": ["MS.125"] },
      "thumbnail": [
         "...": "..."
      ] 
    },
    {
      "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-126",
      "type": "Manifest",
      "label": { "en": ["MS.126"] },
      "thumbnail": [
         "...": "..."
      ] 
    }
  ],
   "totalItems": 4,
   "view": {
      "id": "https://api.iiif.library.leeds.ac.uk/?page=1&pageSize=2",
      "@type": "PartialCollectionView",
      "next": "https://api.iiif.library.leeds.ac.uk/?page=2&pageSize=2",
      "last": "https://api.iiif.library.leeds.ac.uk/?page=2&pageSize=2",
      "page": 1,
      "pageSize": 2,
      "totalPages": 2
  },
  "seeAlso": [
    {
      "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century",
      "type": "Collection",
      "label": { "en": ["14th Century Manuscripts"] },
      "behavior": [ "publicVersion" ]
    }
  ],
  "created": "2024-01-01T12:00:00",
  "modified": "2024-02-01T12:00:00",
  "modifiedBy": "https://iiif.library.leeds.ac.uk/users/tom",
}
```

### Possible Schema for Collections

Both types of Collections live in the same self-referencing hierarchical table:


```sql
create table if not exists public.collections
(
    id                    varchar,
    slug                  text,
    use_path              boolean,
    parent                varchar,
    items_order           integer,
    label                 text,
    thumbnail             text,
    locked_by             varchar,
    created               timestamp,
    modified              timestamp,
    modified_by           varchar,
    tags                  text[],
    is_storage_collection boolean,
    public                boolean
);
```

| Column                | Description |
| --------------------- | ------------- |
| id                    | From id minter service - not a URI but an alphanumeric identifier  |
| slug                  | path element, if addressed hierarchically, defaults to null if not supplied  |
| use_path              | Whether the id (URL) of the stored Collection is its fixed id, or is the path from parent slugs. Each will redirect to the other if requested on the "wrong" canonical URL.  |
| parent                | id of parent collection (Storage Collection or IIIF Collection) |
| items_order           | Order within parent collection (unused if parent is storage) |
| label                 | Derived from the stored IIIF collection JSON - a single value on the default language |
| thumbnail             | Not the IIIF JSON, just a single path or URI to 100px, for rapid query results |
| locked_by             | null normally; user id if being edited |
| created               | Create date |
| modified              | last updated |
| modified_by           | Who last committed a change to this Collection |
| tags                  | Arbitrary strings to tag manifest, used to create virtual collections |
| is_storage_collection | Default false is proper IIIF collection; will have JSON in S3 |
| public                | Whether the collection is available at dlcs.io/iiif/<path> |

>❓See **More on slugs, ids, paths, serving IIIF** for info on parent/child relationships in the IIIF

>❓See notes about DB implementation later on in this document - might want a table just for hierarchy of both manifests and collections, as well as a collections table and a manifests table. (The above is a suggested schema, needs much discussion)

For the previous example, there would be one row in this table, and a JSON file would be stored in S3 at `s3://iiif-bucket/collections/pbf237mc.json`.

The ID minter service mentioned above should be something like https://github.com/digirati-co-uk/id-minter - but this should be pluggable, so that the IIIF-CS platform can request ID generation from an external service. For Leeds, they will have a central ID minting service.

### Collections and Storage Collections Summary

* Why the same table? Because both are containers, and you can convert from one to another
* Storage Collection has no stored JSON in S3, entirely DB driven, can't carry any IIIF that isn't in DB, just a projection.
* Storage Collection has pager attached and additional context for it.
* Also possible to have virtual collections based on queries, which behave like Storage Collections

>❓In the CRKN prototype, the canonical URIs of storage collections end with a trailing slash, and IIIF Collections URIs do not. The presence of the trailing slash is required on PUT as well. That API also allows you to create a storage collection by PUT with no `items` property. THIS NEEDS SPECIFYING MORE FULLY.


### Manifest

Manifests must exist within a Collection - which can be a Storage Collection (even the repository root) or a IIIF Collection.

The following example is the public view of a Manifest with a single image in it. Only some of the possible IIIF fields are shown for brevity.

```json
{
  "@context": "http://iiif.io/api/presentation/3/context.json",
  "id": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-125",
  "type": "Manifest",
  "label": { "en": ["The Leeds Psalter"] },
  "metadata": [
    {
      "label": { "en": [ "Otherwise known as" ] },
      "value": { "en": [ "MS.125" ] }
    },
    {
      "label": { "en": [ "date" ] },
      "value": { "en": [ "c. 1370" ] }
    },
    "items": [
      {
        "id": "...(canvas-id)...",
        "type": "Canvas",
        "items": [
          {
            "id": "...",
            "type": "AnnotationPage",
            "items": [
              {
                "id": "...",
                "type": "Annotation",
                "motivation": "painting",
                "body": {
                  "id": "https://images.library.leeds.ac.uk/iiif/76/MS_125_001/full/1200,/0/default.jpg",
                  "type": "Image",
                  "format": "image/jpeg",
                  "width": 1200,
                  "height": 1885,
                  "service": [
                    "id": "https://images.library.leeds.ac.uk/iiif/76/MS_125_001",
                    "type": "ImageService3",
                    "profile": "level2"
                  ]

                },
                "target": "...(canvas-id)..."
              }
            ]
          }
        ],
        "thumbnail": [
          { "...": "...(omitted for brevity)" }
        ]
      }
    ]
  ]
}
```

This Manifest could have _anything_ permitted by IIIF in it, and saving it back to the platform would retain that information. (See protocol level, below).

#### "painting", PaintedResources, and Assets

A IIIF-CS Platform managed asset appears in this manifest as the body of a `painting` annotation (strictly speaking, as the `service` property of a painting annotation body, although the `id` of the body itself will almost always be a _parameterisation_ of that service - i.e., a particular pixel response from that service).

The API view of this Manifest follows below. Note that:

* The manifest has extra properties like `slug`, `parent`, `publicId` etc.
* The image on the canvas has a `paintedResource` property, which is a single `PaintedResource` with two fields: `canvasPainting` and `asset`. The `canvasPainting` property is always present, it is a shorthand version of the way the image (the _Content Resource_) is associated with the Canvas. The `asset` property is only present if the asset is managed by the IIIF-CS platform - it will be absent if the Content Resource lives somewhere else on the web. It is given as a reference (just `id` and `type`).
* The _painted resource_ is repeated in the Manifest's `paintedResources` list, which restates the information from each canvas but this time gives the full asset JSON, if the asset is managed by IIIF-CS. 
* There is also a **link** to a further `assets` collection, which is the list of assets that have been put in the Manifest as a Container (this acts like the list of assets in a Space (space.images)[https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/space#images]). They aren't necessarily all being used in the Manifest, but they are members of the Manifest in the same way that assets are in a Space. (in fact they _are_ in a Space, a row in the spaces table was created for this row in the Manifests table).
* A Manifest may have members in paintedResources with `asset` properties that are not in `/assets`, and it may have assets in `/assets` that are not used in any PaintedResource. But _typically_, all the assets in the Manifest-as-container are used on the Canvases of the Manifest.

> ❓ The set of assets _contained by_ a Manifest (i.e., in that Manifest's dedicated Space) is not the same as the set of assets currently used on the Manifests's canvases. They could be even be completely non-overlapping, one or other could be empty, etc. A Manifest may use assets associated with other Manifests or no Manifest; it may use resources on the web that are not managed by IIIF-CS. And conversely, you might put 20 assets into a Manifest and have the IIIF-CS process them - just like putting them in a Space - but only later use them (or some of them) on Canvases.

> ❓ I'll try to use the term _Asset_ for something managed by the IIIF-CS platform, and _Resource_ more generally for any images, AV etc that may or may not be managed by the platform.


```json
{
   "@context": [
       "http://tbc.org/iiif-repository/1/context.json",
       "http://iiif.io/api/presentation/3/context.json"
   ],
  "id": "https://api.iiif.library.leeds.ac.uk/iiif/manifests/t454knmf",
  "publicId": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-125",
  "type": "Manifest",
  "slug": "ms-125",
  "parent": "https://api.iiif.library.leeds.ac.uk/iiif/collections/ae45gh7e",
  "space": 76,
  "itemsOrder": 23,
  "label": { "en": ["The Leeds Psalter"] },
  "thumbnail": "...",
  "created": "2024-01-01T12:00:00",
  "modified": "2024-02-01T12:00:00",
  "modifiedBy": "https://iiif.library.leeds.ac.uk/users/tom",
  "tags": [],
  "simple": false,
  "sheet": null,


  "metadata": [
    {
      "label": { "en": [ "Otherwise known as" ] },
      "value": { "en": [ "MS.125" ] }
    },
    {
      "label": { "en": [ "date" ] },
      "value": { "en": [ "c. 1370" ] }
    },
  ],
    "items": [
      {
        "id": "https://api.iiif.library.leeds.ac.uk/iiif/canvases/ae4b77wd",
        "type": "Canvas",
        "label": { "en": [ "Canvas 1" ] },
        "items": [
          {
            "id": "...",
            "type": "AnnotationPage",
            "items": [
              {
                "id": "...",
                "type": "Annotation",
                "motivation": "painting",
                "body": {
                  "id": "https://images.library.leeds.ac.uk/iiif/76/MS_125_001/full/1200,/0/default.jpg",
                  "type": "Image",
                  "format": "image/jpeg",
                  "width": 1200,
                  "height": 1885,
                  "service": [
                    {
                      "id": "https://images.library.leeds.ac.uk/iiif/5/MS_125_001",
                      "type": "ImageService3",
                      "profile": "level2"
                    }
                  ],
                  "paintedResource": {
                    "id": "https://api.iiif.library.leeds.ac.uk/iiif/paintedResources/t454knmf/ae4b77wd/0/0",
                    "type": "PaintedResource"
                  }
                },
                "target": "https://api.iiif.library.leeds.ac.uk/iiif/canvases/ae4b77wd"
              }
            ]
          }
        ],
        "thumbnail": [
          {"...": "..."}
        ]
      }
    ],
  "paintedResources": [
    {
      "id": "https://api.iiif.library.leeds.ac.uk/iiif/paintedResources/t454knmf/ae4b77wd/0/0",
      "type": "PaintedResource",
      "canvasPainting": {
        "canvasId": "https://api.iiif.library.leeds.ac.uk/iiif/canvases/ae4b77wd",
        "canvasOriginalId": null,
        "canvasOrder": 0,
        "choiceOrder": null,
        "thumbnail": null,
        "label": null,
        "canvasLabel": { "en": [ "Canvas 1" ] },
        "target": null,
        "staticWidth": 1200,
        "staticHeight": 1885    
      },
      "asset": {
        "@id": "https://api.dlcs.library.leeds.ac.uk/customers/2/spaces/76/MS_125_001",
        "@type": "vocab:Image",
        "customer": 2,
        "space": 76,
        "origin": "s3://fedora-bucket/...(a fedora OCFL path).../MS_125_001.tiff",
        "contentType": "image/tiff",
        "width": 6000,
        "height": 9000,
        "deliveryChannels": [
          {
            "@type": "vocab:DeliveryChannel",
            "channel": "iiif-img",
            "policy": "use-original"
          },
          {
            "@type": "vocab:DeliveryChannel",
            "channel": "thumbs",
            "policy": "https://api.dlcs.library.leeds.ac.uk/customers/2/deliveryChannelPolicies/thumbs/standard"
          }
        ],
        "...": "...(other asset fields from IIIF-Cloud-Services)",                        
      }
    }
  ],
  "assets": [
    {
      "@id": "https://api.iiif.library.leeds.ac.uk/iiif/manifests/t454knmf/assets",
      "@type": "hydra:Collection"                    
    }
  ]
}
```

The above Manifest has some repetition, but it represents the most common scenario - the assets painted onto the canvases are also the assets "contained by" the Manifest (the same way a Space contains assets). 

* The individual PaintedResources asserted singly on individual content resources will always be repeated in the `paintedResources` property of the manifest. 
* If the PaintedResource has an Asset managed by the platform, _regardless of whether it is in the Manifest's own Space_, it will appear as a reference in the per-content-resource `paintedResource.asset` property (just `{ "id": "...", "type": "..." }` and as the full Asset in the `paintedResources[n].asset` property.
* The `manifest.assets` property links to a collection that lists the assets that "belong" to the manifest, just like space.images. In fact, this property should give exactly the same collection as the API would return for the space associated with that manifest.

By definition, anything referenced by `paintedResource` or `paintedResources` must have a `canvasPainting` property, but will only have an `asset` property if the asset is managed by IIIF-CS.

By definition, ALL the assets in the referenced `assets` Hydra Collection are managed by the platform, and are associated with this Manifest by a containment relationship. But they don't have to be used in this Manifest, and may be used in other Manifests.

> ❓ I have given these PaintedResource objects their own `id` and `type`, to make clients easier. The `id` could be synthesised from slug forms of manifest id, canvas id, canvas order and choice order (although should be treated as opaque by clients).

```json
{
  "id": "https://api.iiif.library.leeds.ac.uk/iiif/paintedResources/t454knmf/ae4b77wd/0/0",
  "type": "PaintedResource"
}
```

**NB** The `assets` property in an API view of a manifest delivered by the IIIF-CS platform is always a linking property (the assets are not returned inline). It behaves like `.../space/images`. However, it is possible to **send** assets inline when PUTting a Manifest (synchronising) in the PaintedResources array, so that we can introduce assets and the information that paints them in the same atomic operation.


### Possible schema for Manifest

```sql
create table if not exists public.manifests
(
    id          varchar,
    slug        text,
    use_path    boolean,
    parent      varchar,
    items_order integer,
    space       integer,
    label       json,
    thumbnail   text,
    locked_by   varchar,
    locked_at   timestamp,
    created     timestamp,
    modified    timestamp,
    modified_by varchar,
    tags        text[],
    simple      boolean,
    sheet       text
);
```

| Column                | Description |
| --------------------- | ------------- |
| id                    | From id minter service - not a URI but an alphanumeric identifier  |
| slug                  | path element, if addressed hierarchically, defaults to null if not supplied  |
| use_path              | Whether the id (URL) of the stored Manifest is its fixed id, or is the path from parent slugs. The one can redirect to the other if requested on the "wrong" canonical URL. |
| parent                | id of parent collection (Storage Collection or IIIF Collection) |
| items_order           | Order within parent collection (unused if parent is storage) |
| space                 | The Space associated with this manifest. Auto-generated when the Manifest is created. Unless a different Space is declared explicitly, newly introduced assets will go into this space. |
| label                 | Derived from the stored IIIF Manifest JSON - a single value on the default language |
| thumbnail             | Not the IIIF JSON, just a single path or URI to 100px, for rapid query results |
| locked_by             | null normally; user id if being edited |
| created               | Create date |
| modified              | last updated |
| modified_by           | Who last committed a change to this Manifest |
| tags                  | Arbitrary strings to tag manifest, used to create virtual collections |
| simple                | One canvas_painting per canvas, no external assets, no non-null targets, no additional resources on canvas that are not known adjuncts or services |
| sheet                 | A Google Sheet or online Excel 365 sheet that the Manifest was created from, and can synchronise with. |


> ❓We should encourage asset IDs _after_ the `/<space>/` part that are still unique to the customer, e.g., include some aspect of the manifest in the asset id.
> There's no requirement that a manifest must use assets from a particular space, they could be from any space.


### The canvas_paintings table

This table stores the relationship between a Manifest in the manifests table above, and content resources. These content resources are _usually_ assets managed by the platform, but don't have to be. This table provides the data for the `canvasPainting` property of the PaintedResource.

This table is designed to be efficient for the 99% use case of one asset per canvas, filling that canvas - but nice to use for other content association scenarios encountered in IIIF. It is modelling four things:

* Canvases
* Painting annotations on the canvas
* Body of the painting annotation
* Choice items if body is a choice

> ❓TODO: adjuncts for Manifests and Canvases
>
> DON'T THINK ABOUT THIS NOW
>
> `seeAlso` and `annotations` come from adjuncts which belong to ASSETS | tbc how we do that for annos

We can project a Manifest from the information in this table, _if that's all we have_. But it deliberately falls far short of modelling all the things that canvases and annotations can have - these only exist in the JSON representation "on disk" (in S3). Updates to the Manifest from the JSON representation can be reflected back into this table. This table holds what we want to query on, but it always reflects _what was in some JSON_ rather than _what JSON should be generated_, **except** when new content is introduced via the PaintedResource, whose fields map to this table. In that scenario, e.g., creating a new manifest from a sequence of PaintedResources, the IIIF-CS platform must populate the table and generate the _initial_ JSON that reflects it.


```sql
create table if not exists public.canvas_paintings
(
    manifest_id        varchar,
    canvas_id          varchar,
    canvas_original_id text,
    canvas_order       integer,
    choice_order       integer,
    asset_id           text,
    thumbnail          text,
    label              json,
    canvas_label       json,
    target             text,   -- could be json, or jsonb
    static_width       integer,
    static_height      integer 
);
```

| Column                | Description |
| --------------------- | ------------- |
| manifest_id           | Alphanumeric id from the `manifests` table above, associates an asset with a manifest  |
| canvas_id             | Canvases in Manifests always use a flat id, something like `https://dlcs.io/iiif/canvases/ae4567rd`, rather than anything path-based. If requested directly, IIIF-CS returns canvas from this table with `partOf` pointing at manifest(s). `canvas_id` might **not be unique** within this table if the asset is `painted` in more than one Manifest |
| canvas_original_id    | A fully qualified external URL used when `canvas_id` is not managed; e.g., manifest was made externally. |
| canvas_order          | Canvas sequence order within a Manifest. This keeps incrementing for successive paintings on the same canvas, it is always >= number of canvases in the manifest. For most manifests, the number of rows equals the highest value of this. **It stays the same** for successive content resources within a Choice (see choice_order). It gets recalculated on a Manifest save by walking through the manifest.items, incrementing as we go. |
| choice_order          | Normally null; a positive integer indicates that the asset is part of a Choice body. Multiple choice bodies share same value of order. When the successive content resources are items in a `Choice` body, `canvas_order` holds constant and this row increments. |
| asset_id              | Platform asset ID (cust/space/id) to be painted on the canvas - may be null if external. This is the resource that is the body (or one of the choice items), which may have further services, adjuncts that the platform knows about. But we don't store the body JSON here, and if it's not a platform asset, we don't have any record of the body - JSON is king. |
| thumbnail             | As with manifest - URI of a 100px thumb. Could be derived from asset id though? So may be null most of the time. |
| label                 | Stored language map, is the same as the on the canvas, may be null where it is not contributing to the canvas, should be used for choice, multiples etc. |
| canvas_label          | Only needed if the canvas label is not to be the first asset label; multiple assets on a canvas use the first. |
| target                | null if fills whole canvas, otherwise a parseable IIIF selector (fragment or JSON) |
| static_width          | For images, the width of the image in the Manifest for which the IIIF API is a service. This and static_height next two default to 0 in which case the largest thumbnail size is used - which may be a secret thumbnail. |
| static_height         | For images, the height of the image in the Manifest for which the IIIF API is a service. |

This is a simple table, but it allows us to express multiple content resources on a Canvas, which may or may not target the full Canvas, and which may or may not be `Choice` bodies.

> https://deploy-preview-2--dlcs-docs.netlify.app/manifest-view.html is an experiment to verify that tabular data like the above can be expressed first as a manifest (https://deploy-preview-2--dlcs-docs.netlify.app/manifest-builder/ms125_full-example.json) and then as a tabular HTML representation in the demo. Note the `paintedResources` property in that example.

The `paintedResource` property in the Manifest example is derived from a row in the assets table and a row in the canvas_paintings table, and provides a mechanism to synchronise assets with their Manifest container at the same time the rest of the constructed Manifest JSON is constructed by a tool like iiif-builder.

> ❓If the canvases are "simple" can can be entirely round-tripped from the table alone, then synchronisation of a Manifest with the platform can _omit_ the `items` property altogether, and instead supply `paintedResource` and `assets` inline. This is the 99% use case for digitised material.
> TODO - canvases and resources will carry additional services and derivatives and renderings - adjuncts. For example, OCR data or IIIF annotations carrying full text. This simple synchronisation mechanism will still hold if the Manifest has adjunct policies and pipelines that determine what each canvas will carry.

You can update a whole Manifest's `paintedResources=>asset` with additional `origin` and `deliveryChannels` info for processing, but in the 99% case this is just an asset with the additional ordering property in the `canvasPainting` property.

> This approach replaces use of string1, number1 for named queries - although you can still set those old fields too - because it's still an Asset and can still have regular string and number metadata, as well as tags.

Because this approach exposes a `canvas_order` and `choice_order` property, you can use it do **insertions** of assets with simple synchronisation.



### Comparison with IIIF-CS Spaces

To add assets to a manifest, you can POST batches for processing to a queue.

Therefore the Manifest has an endpoint:

* `(manifest_id)/queue`

This behaves just like a regular [queue](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/queues) but does not require that incoming assets in batches declare the Manifest they are for. If they do declare a space, it must match the manifest's space, otherwise it's a bad request. But you usually wouldn't send a space. (0 counts as no space). 

**This is a queue just for this manifest's space.**

And just as a space has assets, so does a manifest:

* `(manifest_id)/assets` - a hydra Collection, the same result as the manifest's space would return.
* `(manifest_id)/paintedResources` - The same as the inline property, but you can POST individual PaintedResources or collections of PaintedResources to this endpoint _as if it were a queue_ - and insert assets/canvases into the manifest.

_See below for usage scenarios_

> ❓When using api.dlcs.io, manifest has /queue and /assets in extra service block, not present in public version. dynamically added. Both api.dlcs.io/...manifest and dlcs.io/..manifest are proper manifests. 



The public facing API can also expose:

* `(manifest_id)/search`

... to provide IIIF Search API

> ❓This requires a separate RFC along with adjuncts and pipelines. 

* `(coll_id)/search`

The platform allows for IIIF Collections to expose a Search function _across manifests in the Collection_.

> ❓(This is a phase 2!) 

> ❓ I was thinking of adding a new field `manifest_context` to asset, which is the ID of the Manifest that introduced the asset to the platform. But this is redundant if we ALWAYS create a space for the manifest - the asset lives in that manifest's space, so given an asset, we can see it's space, and if that space is a Manifest's space, then that is the asset's manifest context. This stays the same even if the asset is further used in other manifests. Usually it only gets used in one. This is a useful to build orphan deletion candidate lists.

### Common Features of Collections

Allowed create operations:

* Creating a Storage Collection within a Storage Collection
* Creating a IIIF Collection within a Storage Collection
* Creating a IIIF Collection within a IIIF Collection
* Creating a Manifest within a Storage Collection
* Creating a Manifest within a IIIF Collection

**Disallowed** operations:

* Creating a Storage Collection within a IIIF Collection
* Creating a Manifest within a Manifest
* Creating a IIIF Collection within a Manifest
* Creating a Storage Collection within a Manifest



### REST operations

Clients can choose whether to update manifests by POSTing Manifest JSON or by POSTing Platform API assets / paintedResources with assets, depending on the scenario. Any additional per canvas and hoc JSON must be persisted by sending IIIF Manifest JSON and letting the platform take care of merging that into the table. A Canvas can carry anything, and this is one of the main challenges with this approach. We will still need to establish a sensible order of precedence.


#### Creating a new Manifest

A very simple approach would be to just POST or PUT a very minimal JSON body to create the Manifest, with `id`, `type`, `label` as minimum (can have more), and then post assets to its queue.

For example:

PUT this manifest to a path:

```json
{
    "id": null,  // 
    "type": "Manifest",
    "label": { }
}
```

... and then POST a `PaintedResource`, or a Collection of `PaintedResource`, to `(@id)/paintedResources` to add canvases.

Or inline:

```json
{
    "@context": [
       // both contexts
    ],
    "id": null,  // 
    "type": "Manifest",
    "label": { },
    "paintedResources": [
        { 
          "canvasPainting": {}, // where to insert this in the Manifest
          "asset": {} // including origin, optional delivery Channels, roles, etc
        },
        // and more....
    ]
}
```

This way, **we can synchronise the manifest and its assets _together_**: "Here is a manifest, with its assets." You could create a manifest with initial assets like this. It comes back with a regular `items` property (although may not be fully populated with height and width yet). A batch will have been created. This batch could be retrieved from the queue.

**The above is a synchronous operation, like posting a batch. You can get the manifest back right away - BUT ITS ASSETS MAY NOT YET BE FINISHED PROCESSING. We might not yet know dimensions. Individual assets will have `ingesting: true`, and the Manifest as a whole will have a variant of this property:

```json
{
  "ingesting": {
    "finished": 37,
    "total": 123
  }
}
```

> ❓ We might want to just list batches created there. That allows us to have exactly the same batch behaviour as well as set a ceiling on the number per batch. However, what do we do about very large manifests - a user sends a single manifest with 1000 items in `paintedResources`... what happens? 

Once each asset has finished ingesting, the Manifest will show complete information and will also automatically show the `thumbnail` property on Canvases for image assets, generated from the thumbs Delivery Channel configured sizes (just as in current NQ or single-asset manifest).

A client could edit this resulting Manifest as JSON (in a text editor, or a visual Manifest Editor) and PUT it back, just as normal IIIF. The Platform is able to recognise its own assets in the regular IIIF (not just in paintedResources) and go back and forth between IIIF and PaintedResource representation. It can even do this when rewrite rules are in operation.

> ❓The platform needs know about any rewrites and be able to transform them both ways. How it does this is TBC. It needs to both recognise incoming assets and turn them into the API paths, and also write the public-facing URLs into outgoing IIIF.

A client can reference existing or external assets, including assets in other manifests (assets where there is no containment).

BUT a client cannot introduce an asset to the system from a purely IIIF representation of _what it's going to look like - using the eventual public facing URL_ - there's not enough information (`origin`, `deliveryChannels` and so on are missing). An introduced, new Asset must come into the system as a "proper" Asset / PaintedResource.

> * The PaintedResource.asset contains extra things used at ingest time but then reflected back in generated IIIF as order, auth services etc.
> * The IIIF Canvas also has any valid additional IIIF. 
> * The platform needs to be able to merge these.

The IIIF and paintedResource's asset are a Venn diagram, each can have some things the other doesn't, but the paintedResource's asset extra fields only relate to ingest (or reingest) information. they do not dictate what comes out in the public Manifest, except where consequences such as Auth services are present (because the asset had roles).

If instead you PUT a Manifest to its API URL, that incoming Manifest may have:

* Completely standard IIIF referencing both IIIF-CS-managed and external resources. It can reference platform existing resources (assets) that weren't previously in the Manifest, or were in a different Manifest, or are existing assets in spaces. But you can't introduce an asset for the first time like this.
* Standard IIIF but with additional asset body attached to the content resource.
* A `paintedResources[]` property providing the assets to be used and where they live in the Manifest (via the `canvasPaintings` property), with or without the plain IIIF. 

Because we also expose `paintedResources` as a separate collection, you can have a cleanly separated Asset sync and IIIF Creation step. Most Canvases can be built entirely from the paintedResource info and pipelines declared for the manifest. But even when that isn't the case, the robust IIIF <-> sync preserves additional information.

> ❓The MODEL behind the Manifest View in the portal is a manifest with both `items[]` and `paintedResources[]` properties.

> ❓ Need to think about what happens when an update of a Manifest includes canvases and paintedResources that disagree with each other. Also the scenario - may be useful in iiif-builder - where the canvases are present in an incoming manifest, but the `canvas.items` properties are not. This pattern allows callers to hang whatever custom stuff they want on the Canvas, but then treat all the content more simply as IIIF-CS managed assets.

### Scenario for a client like a Manifest Editor

While an automated workflow suits synchronising painted resources (to avoid sync code having to construct complex IIIF), a Manifest Editor is already handling the complex IIIF. It might not want to use those IIIF-CS-specific extras at all, but _still want to allow users to ingest assets for their manifests_. Also, a Manifest Editor is likely maintaining the editing state of a Manifest, and doesn't want to PUT it back to the server as part of the process of the user adding a new image (for example). 

This is where the `(manifest_id)/assets` endpoint is likely to be more useful - you can add assets here without any impact on the Manifest itself, but because the set of assets are scoped to the Manifest, they act like a tray of resources you can use in your Manifest. So a user might create an Manifest in the Manifest Editor, save it once (to establish a row for it, and therefore an /assets endpoint), then independently (but still from the Manifest Editor) upload an asset to /assets (or specify an origin, etc), and then _later_ use that asset on a particular canvas - saving it back as a "image with image service" just as if it were any external image service. The IIIF-CS recognises its own resources and can create the correct canvas_painting rows, and that paintedResource will appear in the Manifest next time it is fetched with GET.

## Locking

In the current IIIF-CS platform there is no concept of locking an asset for editing, or versioning an asset. This is fine because operations on assets are _individually_ short lived and atomic. But Manifests and IIIF Collections are potentially much more complicated, especially when those Manifests become content, with editorial, for exhibitions and so on. Even for simple use cases, the fact that the platform is a _repository_ for IIIF requires some degree of concurrency support for clients of the API.

An HTTP `GET` of a Manifest that includes an additional request for a **lock** in the form of an HTTP header (syntax TBC) returns an alt-location in a response header:

`.../<manifest-id>/locked` 

...that a client can make PUT calls to. When locked, there is another "working" manifest in S3 that handles updates from the API (even via a UI). This working Manifest only replaces the original on PUT to original URL, which unlocks and removes the locked version. When locked, **only the user who created the lock can make that PUT**; when not locked, any authorised user can.

> ❓Is that enough? Or... there's no /locked resource, but when you GET with the "want a lock" header, you get an additional token back, as well as the ETag. You present this token in another header to unlock - which may be on a PUT, but could be on an empty POST to unlock without saving. Find a good pattern from an existing application for this.

This transaction is only scoped to the Manifest; assets introduced while locked will still be added to the platform; if you then delete some and save those assets will be deleted too if they are belong to the manifest.

Locking is not required - it may be unnecessary overhead for a process like iiif-builder where other actors trying to edit the same resources is VERY unlikely. But the system will still prevent overwrites when when no locked was acquired, because use of ETags is mandatory (see below).

Any request for the Manifest while locked will return the original, with an HTTP header indicating that it is currently locked.

> ❓ What's happening in the canvas_painting table when the Manifest is locked? Are rows being updated or is the data being stored in a locked_canvas_painting table, or not even being stored at all other than implied in the JSON itself?

## Versioning

We can optionally save a timestamped copy of the previous version whenever a new version is saved.

Under s3 sub-key /versions

/versions/20240303144512  (1-second granularity like memento)


## ETags

A client must take note of the ETag returned with the response for an `api...` Manifest (or Collection), and send the same eTag on any PUT or POST that updates the Manifest.

> NB this is more fully developed in the CRKN prototype. - [See examples](https://github.com/tomcrane/iiif-repository/blob/main/ProtocolTests/PutTests.cs#L95)

We still need to respect this when locked, still require client to send eTag on save: double protection. 

These two mechanisms (locking and eTags) are independent and locking is more useful for UIs like a Manifest Editor in a multi-user environment. You don't have to acquire a lock - but you run the risk of not being able to save your work if you don't, because someone might have updated the Manifest (and therefore generated a new eTag) behind your back.

A PUT with a valid eTag will create a new version without having to acquire a lock first (though will fail if it is actually locked at the time).

This allows human usage in a shared portal alongside machine usage through workflows.

Machines can do what they want without locking.

There is also API to kill a lock; and locks expire after a pre-configured timeout.




## Serving IIIF to the public

 - There is a Presentation API equivalent of the Orchestrator, although it never moves files around and is more purely a proxy.
 - IIIF Manifests and Collections are served by proxying S3, ideally with no DB query at runtime (like thumbs).
 - I suspect we will need a path query to locate the flat manifest S3 key, and then some modification of the JSON read from S3 to update `id`. But we shouldn't do extensive rewriting of asset paths; they should be stored in S3 in their rewritten form. This means that if you change rewrite rules, you need to regenerate JSON.
 - The IIIF-CS API allows you to make a Manifest by solely submitting JSON, by solely adding assets, and by a combination of these two operations.
 - IIIF-CS recognises its own assets in Manifest JSON, and therefore needs to understand where rewrite rules are in effect


### More on slugs, ids, paths, serving IIIF

Manifests, collections, storage collections have string IDs that are flat, and are stored in S3 under these IDs (with .json on the end)

* `s3://iiif-bucket/99/collections/ae45gh7e.json`
* `s3://iiif-bucket/99/manifests/t454knmf.json`

These ids are user supplied, from a minting service, or an ark service. The customer ID here is 99. The varchar IDs are globally unique, but it is still useful to partition by customer, if only for reporting.

You may choose that their PUBLIC urls, and the URLs stored in `id` in the JSON, are paths like https://dlcs.io/iiif/manifests/t454knmf.json. This is a "flat" layout - all Manifests are immediate children of the path ../manifests/.

But you might prefer that a hierarchy is present - of Storage Collections, multiply nested, containing further IIIF resources.

The `slug` property allows us to provide a URL like:

`https://dlcs.io/iiif/special/14th-century/germany/my-manuscript.json`

... because we have collections (probably storage collections) with slugs `special`, `14th-century`, `germany` and a manifest with the slug `my-manuscript.json`

This means we can move and rename things (e.g., the special slug) without having to move thousands of files in S3, they live at their `s3://iiif-bucket/manifests/-id-.json` keys always. 

But that gives us two problems:

 - how do we locate the incoming path in S3 to serve?
 - If the `id` in the stored JSON reflects the path, we need to update lots of S3... so we don't have to move files but we do need to edit them.

This suggests that you have to do a DB query to find the manifest, and you have to replace the `id` with the DB-implied version.
But then we've lost our "almost static" implementation.

This isn't a IIIF problem it's a "storing docs flat on disk with hierarchy in DB" problem which must have a good pattern.

### DB implementation note

Assuming the Collections table above, we need two types of query.

One is a fairly standard recursive CTE query that aggregates the `slug` value - given an `id`, what's the path?

The other is trickier - given a path, what's the ID?

I have done _something_ like this before - see [this Confluence page](https://digirati.atlassian.net/wiki/spaces/WDL/pages/59113782/Postgres+to+SQL+Server).

It may be easier and more performing to make the collections table actually a _hierarchy_ table, so that there is a stub row for Manifests, too. That allows the two queries above to only operate on one table to go either way path<==>id (you'd then need to select the manifest row).

Something like:

```sql
create table if not exists public.hierarchy
(
    id                    varchar,
    slug                  text,
    parent                varchar,
    -- .....
    is_storage_collection boolean,
    is_manifest           boolean,
    is_iiif_collection    boolean,
    public                boolean
);
```

I've added three `is_***` for clarity but could do this other ways. Given a path, you don't know if it's a Manifest or a Collection until you resolve a row for it in this table. 

We could completely **separate out the hierarchy fields**, or (more efficient but less elegant) this is a hierarchy and collections table, you only need to read a row from the manifests table if the row you obtain from here is a stub `is_manifest` row. OTOH, a **pure hierarchy table** could just have `collection_id (null)` and `manifest_id (null)` columns and you always go to the respective table to get the actual row. Or outer join them both to the hierarchy table.

In PostgreSQL we could perhaps use ltree data types to help - this I assume will improve performance and may make the queries easier to understand.

* https://stackoverflow.com/questions/4048151/what-are-the-options-for-storing-hierarchical-data-in-a-relational-database
* https://www.postgresql.org/docs/13/ltree.html 

and see "Moving a Branch" in here:
* https://patshaughnessy.net/2017/12/14/manipulating-trees-using-sql-and-the-postgres-ltree-extension

If we do use ltree, there's another question. Are the elements of the ltree paths the same as the slugs? I don't think they can be, because:

* the ltree separator must be a dot `.`
* the allowed element values are limited to `[A-Za-z0-9_]` 

It would be better if the ltree separator were a slash `/`, but it's not. And I think it is absolutely essential that `.` is permitted in a public slug, as well as `-`. We've used both in examples above already. So we need some private escaping of our (only slightly) wider set of slug characters into permitted path element characters. An incoming query will see the public path, and needs to turn it into the ltree path to query on.


### Manifest Editor and hierarchical paths

As already mentioned, a Manifest Editor probably wants to work with pure IIIF and not the IIIF-CS extensions. Its use of the services may be "to the side", to register assets for use in the Manifest, but not all in one operation.

It might not even want to _see_ all the extra stuff we have in the Manifest.

If we choose Option 3a from [Endpoints](020-files/api-endpoints.md), and the IIIF-CS account is configured to serve a public hierarchical view (the default), a Manifest Editor could:

* Always GET Collections and Manifests without the explicit header
* POST new Manifests and Collections to their parent hierarchy container (like the CRKN protocol)

> ❓ In this scenario, where does the Manifest Editor get Canvas IDs from? It would have to mint its own because it can't see the system canvas IDs until after the fact (it's this kind of thing that paintedResources avoids).




---

IGNORE BELOW HERE

POSTed manifest for ingest 

- may be to a space, not for storage as manifest just as asset carrier and is discarded once its assets are extracted.
- may be to a coll for IIIF. Needs ingest block which is basically an asset, or a paintedAsset (what did I mean by this)



Tasks 

- unpack every single cookbook recipe to the canvas_paintings table including a super-manifest made of all the canvases there
- reverse the process back to IIIF
- do the same but with a super manifest with extra stuff on canvases that must be round-tripped, needs to store original JSON
- demonstrate reordering and insertions don't break this.

- playwright tests


## Synchronisation

For Wellcome, Leeds, etc it's about synchronisation.
This is also true of binding to a sheet - does the manifest still reflect the sheet?

"Does the DLCS have the assets I want to it have for this manifest, with the correct properties, services, roles and adjuncts?" if not, sync. 

The same is true for Collections, although they are much simpler to sync - does this collection have the manifests I think it should have?

This shows up the difference between synchronising the assets and synchronising the rest of the IIIF information, they are different kinds of operations.

For Wellcome at the moment, the client (DDS) queries the DLCS for the assets it thinks it should have for a manifest.
This would be simpler as it wouldn't use an asset query, the manifest is already defined.

Is it worth offering something else? Sending all the assets you think should be there, and allowing the DLCS itself to do the sync?
YES I've now described this above

How would you send them - array of painting assets? How does the portal send them?
Yes, like this

For a sheet binding, is it the portal doing the sync job?
yes I think so

Basically how much support for a Sync Job should the DLCS offer?
What if I just send in a full Manifest via the API - then it has to do some sort of sync.

What's the portal doing when you're saving a manifest? Sending the full manifest, or sending assets in a batch? Depends what you are saving.

Adding assets to a manifest

"Here's what I think you should have"


--------------

Below this line, not developed in this RFC

### Adjunct

### Pipeline

----

Difference between default pipelines for space, customer etc and inherited pipelines that will actually run

If I create a manifest it gets the customer default pipelines

But... a Storage Collection could have both pipelines and default_pipelines.

The former are run for anything added to it, the latter are applied to things created within it...
Is there a difference?


Search service. Generated from text adjuncts. Search within.

other services?

Other pipelines:

Text for client-side search tools
LLM input data
Images in printed books


Adjunct with origin needs additional proxy/copy flag - not just rely on optimised origin behaviour (edited) 

`remote` property