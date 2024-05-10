# Storing IIIF Presentation API resources

## Introduction

A key element of DLIP is the production and serving of IIIF Manifests, and related IIIF API resources such as Collections and Annotation Pages, as well as resources derived from IIIF Assets and Manifests through machine- and human-driven processes (OCR, transcription, tagging, image analysis, entity recognition).

At first, all of those IIIF Manifests will be representations of digital objects stored in Fedora, and will be produced by an entirely automated process from earlier workflow on the objects in Goobi (for digitised items) and in the to-be-built DLIP Preservation UI / Deposit Service (for, mostly, born digital items).

Later on, there are likely to also be Manifests produced all or in part _manually_ - for exhibitions, for storytelling, for driving web user experiences in addition to rendering items. Manifests might also be created for teaching purposes. A Manifest might be assembled from scratch, or might be derived from an existing, automated Manifest. Manifests might combine images and other assets from different IIIF sources. 

We don't want to be too prescriptive at this stage, but it is clear that a flexible "IIIF Platform" is a crucial part of the DLIP strategy, a key enabler of a wide variety of features and services powered by IIIF, as described in the original Technical Discovery work. The platform needs to do all it can to help applications _build_ IIIF Presentation API resources, and to safely serve them at scale. It also needs to act as a IIIF Presentation API Repository, to store arbitrary IIIF Manifests, Collections and possibly other resources arising across the Library's activities, and serve that IIIF to the public, or restricted groups.


### Is IIIF-C this platform?

_Partly._ Digirati's IIIF Cloud Services Platform (developed for Wellcome and referred to by them as the DLCS) is _asset centric_ - give it an image, it will provide a IIIF Image API endpoint for it. Give it a video, it will provide web-friendly transcodes. Give it a PDF or in fact any file, and it will serve it - all of these services protected by the interoperable IIIF Authorization Flow API, integrated with your _Identity Provider_.

It does much more than this - its API allows _management_ of those assets, assignment of arbitrary metadata to those assets, and projection of asset sequences into IIIF Manifests, Zip files and PDFs. An example of this was given in the Storage API demo, where the contents of a Fedora Archival Group were registered with the IIIF-C platform, and used to generate a IIIF Manifest.

But it doesn't have a notion of a IIIF Manifest (or Collection) as a resource that it is storing and serving.


### Prior art

#### Named queries and Skeleton Manifests

A common pattern for use of IIIF Cloud Services is to register assets with at least two metadata fields - one to **group** a set of assets together (e.g., 37 assets all with the string metadata value "book-995"), and one to order them (e.g., those same 37 assets have an ascending integer metadata field that runs from 1 to 37). Then, use the _[Named Query](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/named-queries)_ feature to *project* those assets into what we usually refer to as a _Skeleton Manifest_ ([here's an example](https://dlcs.io/iiif-resource/wellcome/preview/5/b31477707) - this JSON is the projection of a query into IIIF-Manifest form).

We can then load the skeleton manifest using a IIIF library in the programming language of our choice, or load it as a plain JSON object, and _decorate_ it with the information we require (labels, metadata, rights statements etc), saving it _somewhere else_ where it becomes the published official Manifest for the item. This approach can work well for small collections, but it's not very controlled.


#### Wellcome's IIIF Builder

At Wellcome, Manifests and other non-asset IIIF resources are built by a very complex application [iiif-builder](https://github.com/wellcomecollection/iiif-builder) that in parts even pre-dates IIIF itself; it has been worked on since 2012 and has outlasted changes of Digital Preservation platform and sources of descriptive metadata (its first incarnation integrated with Preservica and the Sierra LMS).

* It understands both Goobi METS and Archivematica METS - sources of technical, administrative and structural metadata about digital objects
* It understands the Wellcome Storage Service - a source of descriptive metadata about digital objects
* It understands the IIIF Cloud Services API and synchronises assets referenced by METS files with that API, for asset delivery as Image Services and AV derivatives 
* It seeks out METS-ALTO and other OCR files referenced in METS and builds textual representations, which then power:
  * Search Within (within a Manifest only) using the IIIF Search API
  * W3C web annotations providing a text layer to IIIF clients that understand them
  * Full text downloads
  * W3C web annotations identifying the boundaries of figures in printed books and other material
* It builds its IIIF Manifests independently of the asset delivery services, and provides them on the web ([example](https://iiif.wellcomecollection.org/presentation/b31477707))
* It understand's Wellcome's Catalogue API and what it needs to use from that in the production of IIIF Collections (for archival hierarchy, multi-volume works and periodicals) and Manifests.
* It is resilient to large-scale harvesting of Manifests and text resources (e.g., by bots - an increasing problem).

Despite all these features, its treatment of IIIF Presentation API resources is entirely _derivative_ - there's no possibility of creating a IIIF Manifest externally and using iiif-builder to store it and serve it. It's powerful but inflexible, and completely tied to its sources. This is not a problem for its intended purpose and current use at Wellcome.

It has MANY features we would want to use in DLIP, but they are tied to producing IIIF in one way only. They can't be driven from outside. 

Wellcome's iiif-builder pre-dates the IIIF Cloud Services (or DLCS) and even in part pre-dates IIIF; t was necessarily bespoke and complex _before IIIF came along to give a clear dividing line between open standards and local implementation details_.

#### "Presley"

Over the years, Digirati have built several different implementations of an IIIF Presentation Server, usually with the "Presley" project code name - an environment in which IIIF Manifests can be created and enriched. With all of these, the level of granularity of storage has been a problem. Whole Manifests as JSON objects? Decomposed individual parts of the model, independently editable? 

#### Madoc

These various IIIF storage approaches are most developed in [Madoc](https://madoc.digirati.com/).

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

 - Granularity of backing storage - from blobs of JSON for whole Manifests, to a schema that captures every aspect of IIIF; or even a triple store
 - Granularity of CRUD operations - can I patch in an additional image, or modify a metadata field, or am I always updating a whole Manifest?
 - Integration with asset delivery - is the IIIF store wholly independent and unaware of how image services and AV resources are actually served? Or is it able to bootstrap the creation of IIIF Presentation API resources and integrate it with asset registration? That is, is there a concept of "here is a Manifest and here are the studio TIFFs that comprise it, in the right order... please make something that will work on the web... produce a Manifest that points at IIIF Image APi endpoints derived from those TIFFs"
 - Richness of additional services - from the IIIF-model-only REST protocol for the Manifest Editor, to a rich suite of _derived_ services like search within, search across, enrichment pipelines (see below), storage of adjuncts (see below) associated with or derived from assets.

At Wellcome, interactions with the IIIF-C platform (DLCS) are about asset registration and synchronisation. Knowledge of what assets are needed for a particular manifest, and the order they are needed in, is encoded in [stringN](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/asset#string1) and [numberN](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/asset#number1) fields but means nothing to the platform itself. However, this synchronisation behaviour is very powerful and useful. Abandoning this in favour of a manifest-first approach, such as might be constructed in a manifest editor or programmatically, might be brittle or overly complicated for large scale digitisation workflows.

Can we synchronise a Manifest (the structured digital object) with its assets at the same time? Combine two very distinct activities in the current Wellcome DLCS into one logical synchronisation operation? That would be very powerful. But...

...We want to be able to store _ANY_ manifest or collection in the platform:

 - manifests where all referenced assets and adjuncts are also managed by platform
 - manifests where some are, and some are external
 - manifests where ALL are external (or _unknown_) - a purely Presentation API storage service, like CRKN, with no services provided for assets themselves.

But we also want to benefit from asset queries and Wellcome-style synchronisation of platform assets with the assets asserted in METS files. [Batches](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/batch), [queues](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/queues), and other workflow-friendly processes. It won't be good enough to add assets only through the lens of a Manifest, building the Manifests separately and storing them in a IIIF Repository.

For Leeds we want to synchronise the platform's stored manifest and its assets with the METS as a whole, with additional semantic metadata, adjuncts (see later), enhancements and derivatives. 

> As described in the Technical Architecture there will still be a need for a IIIF-Builder, but rather than it doing _everything_ as at Wellcome, it leans on the services of a much richer IIIF Platform. This richer platform, by making many of those Wellcome services more generic, serves as a foundation for Leeds to build multiple IIIF powered applications as part of DLIP and in the future.

At the moment we can't provide the same suite of services as Wellcome without re-writing them in a Leeds context - so if we are going to do this, we should do this in a way that allows multiple services to be built on top.

### What we have learned from the above

For storing IIIF Manifests that may be edited by external processes, we don't want to deconstruct and reconstruct the Manifest from some other internal representation (a relational schema, a triple store, fragments of JSON). IIIF is very flexible but also very variable; if we commit to some kind of decomposition on receipt of a IIIF payload, we add a new layer of complexity and fragility to the platform.

* IIIF Manifests are the unit of distribution and therefore the unit of persistence; if we create a Manifest, we need to save it again whole.

***BUT...*** sometimes we **do** want to generate and manipulate IIIF without having to think about the whole Manifest. At its simplest, you can conceive of a Manifest as a sequence of assets - I have 20 JPEGs, turn them into a Manifest, give it a label - and I have something publishable. We need more than just a Manifest-sized JSON-blob-store when projecting a Manifest out of a series of assets, or finding out where assets are being used, or adding an asset to a manifest. There's more to storing IIIF than a generic JSON document store, and for large-scale digitisation workflows, we want the platform to assist the construction of IIIF using simple patterns.

Where's the middle ground?

* A [CRKN-like protocol](https://github.com/tomcrane/iiif-repository/blob/main/ProtocolTests/PostTests.cs) for manifests, but with added asset synchronisation features.
* Where the Manifest can be thought of as a Container or organisational unit of an ordered sequence of assets...
* But can carry arbitrary additional information, and complex _Canvas Composition_.

In the current IIIF Cloud Services platform, there is no notion that assets are members of any larger set, except in two ways:

1. We can organise them into [spaces](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/space), which allow for different default policies
2. We can impose our own metadata so that we can use it to generate [named queries](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/named-queries).

We could use the existing Space resource to represent manifests (one space per manifest), but we would still need the second technique to assign ordering within the manifest. And there's still nowhere to "hang" all the additional information we want the manifest to carry. Spaces are more of an orthogonal partitioning mechanism, used for organising assets at a larger scale (e.g., Wellcome's Space 5 has 56 million assets in it).

This RFC proposes new storage concepts to be introduced to IIIF Cloud Services:

* Manifests, that can contain assets, similar to the way spaces can contain assets
* Collections, that can contain Manifests or other Collections, but that come in two flavours:
  * IIIF Collections - e.g., to represent multi volume works, periodicals etc
  * Storage Collections - like folders to organise the storage of IIIF resources within the platform

Assets can be "added" to Manifests, and the platform will generate an initial IIIF Manifest from the assets within a Manifest container. You could create a Manifest by adding assets into it.

* A **IIIF Manifest** always has a stored JSON representation, that can carry any information that we can model in IIIF - the JSON representation is a IIIF Presentation API 3.0 Manifest.
* A **IIIF Collection** always has a stored JSON representation.
* A **Storage Collection** may simply be a container, but the platform can express it (make available as API) as a IIIF Presentation API 3.0 Collection if we want it to be exposed that way. We can't add arbitrary additional IIIF properties to such a Collection, but crucially it is _navigable_ by anything that understands a IIIF Collection.
* An asset can appear in multiple Manifests if required - it's not confined to the Manifest it was put into.
* A IIIF-C stored Manifest can reference IIIF Image API endpoints and other content resources (images, AV, etc) _that are not being provided by IIIF-C_. An IIIF-C stored Manifest can have all of its assets registered with IIIF-C (the standard model for Digitised and Born Digital workflows), or some of them, or even none of them. This latter scenario is like the CRKN protocol.
* The platform offers helper APIs to manipulate assets within a Manifest. 
* We should make it easy to write _synchronisation code_ so that a much simpler iiif-builder component can apply changes from METS files to IIIF Manifests.
* iiif-builder is just one client; IIIF Manifest Editors, exhibition builders and bespoke tools are also clients.

And from these emerge usage scenarios:

* Create a new manifest, POST new assets into it like a container, but you can see it served as a IIIF Manifest
* Fetch the Manifest, manipulate it, add arbitrary additional IIIF (e.g., label, metadata) and save it back
* Add additional assets easily
* Associate textual content with IIIF Canvases within the Manifest
* Generate Search Within services for a Manifest from that textual content
* Transform that textual content into IIIF-native forms (Annotations) from other formats (e.g., ALTO, hOCR)
* Transform textual content into web-native forms for innovative UI (SVG, plain text)
* Generate Search services for whole Collections, and more generally across Manifests

#### IIIF Structure

A Manifest is not just a sequence of assets; a Manifest's `items` property is a sequence of Canvases, each of which has one or more Annotation Pages, each of which has one or more Annotations, of which at least one is usually an Annotation with the motivation `painting` that provides the Canvas's content. This multi-level structure is what gives IIIF its power but we should be able to _safely_ bypass it for simple operations - that is, don't force API consumers to navigate this structure just to add an asset to a Manifest, but don't pretend that the structure doesn't exist and prevent the use cases that need this structure.


## Implementation

Throughout the following text we will use the URL `iiif.library.leeds.ac.uk` as the root of the IIIF Cloud Services platform - the public facing accessible contents, and `api.iiif.library.leeds.ac.uk` as the endpoint for manipulating IIIF via the IIIF-C API. If we want to create manifests, edit them, view additional properties, it's on the `api.iiif..` hostname, a JSON REST / CRUD API secured with OAuth2.

When serving IIIF Presentation API resources to users over the web, it's on the `iiif...` hostname - still serving (mostly) JSON, usually (but not always) open, without access control.

The "same" resources are available on both hosts, but the representation is much richer on the API host.

### Storage Collection

A Container that does not have a JSON representation. It's simply a container. We can't add IIIF `label`, `metadata` or any other fields to it. there is no JSON representation of this resource stored in S3 or anywhere else, it's entirely dynamically generated (see schema suggestion later).

`https://api.iiif.library.leeds.ac.uk/` is the root storage collection.

The API response that comes back from that endpoint is a **valid IIIF Collection**, with an additional `@context` that allows us to attach a _pager_ to our Storage Collections, and other properties (more later):

```json
{
   "@context": [
       "http://tbc.org/iiif-repository/1/context.json",
       "http://iiif.io/api/presentation/3/context.json"
   ],
   "id": "https://api.iiif.library.leeds.ac.uk/",
   "type": "Collection",
   "behavior": [ "StorageCollection" ],
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

The `view` property is one that the [IIIF-C API uses already](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/collections), on non-IIIF API resources - for example paging through a space. The `PartialCollectionView` is from the [Hydra hypermedia API Specification](https://www.hydra-cg.com/spec/latest/core/#collections) that the IIIF-C Platform uses for all non-IIIF API operations.

In the above example there are 4 items that are immediate children of `https://api.iiif.library.leeds.ac.uk/`, but requesting that resource directly only indicates two of them in the initial response. We can use the PartialCollectionView to navigate to the others, and the `totalItems` property to see how many items altogether. Here the default page size is 2 to keep the example small, it would obviously be much larger (100 or more) in the production API.

The `seeAlso` property links to the public view of this collection _if there is one_ - it's optional whether a storage collection has a public representation. You might have a "folder" with 100,000 Manifests in it; there is no need for this to appear to the public.

>❓How to govern this visibility - how do you as an API user specify the behaviour? `isStorageCollection` on Collection table, StorageCollection `behavior`

The public version (if published):

* has only the IIIF `@context`
* is not paged (no `view` or `totalItems` properties)
* does not link back to the API version
* does not have a qualifying `behavior` property.

### IIIF Collection

A Container that is also exposed as a IIIF Collection. A JSON representation of this resource is stored on disk. The platform also maintains the containment hierarchy information in its database schema. An update to the Collection resource is at the level of the Collection JSON (a PUT or a POST), and the platform needs to parse and translate the implied members and store them in the Collections table (see suggested schema below).

>❓We could be stricter here and separate out the `items` property of our IIIF Collection and have that entirely managed by relational schema. Every other bit of IIIF is in the JSON file in S3. That would mean that you can't add arbitrary properties to resources underneath `items`, which may be limiting in some use cases. But it would be more robust and potentially more useful.

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
   "type": "Collection",

   "slug": "14th-century",
   "usePath": true,
   "idInJson": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century",
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
    id_in_json            text,
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
| use_path              | Whether the id (URL) of the stored Collection is its fixed id, or is the path from parent slugs. The one can redirect to the other if requested on the "wrong" canonical URL.  |
| id_in_json            | The id of the Collection last time it was persisted to S3 |
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

(The above is a suggested schema, needs much discussion)

For the previous example, there would be one row in this table, and a JSON file would be stored in S3 at `s3://iiif-bucket/collections/pbf237mc.json`.


### Collections and Storage Collections Summary

* Why the same table? Because both are containers, and convert from one to another
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

#### "painting" and paintedAssets

A IIIF-C Platform managed asset appears in this manifest as the body of a `painting` annotation (strictly speaking, as the `service` property of a painting annotation body, although the `id` of the body itself will almost always be a _parameterisation_ of that service - i.e., a particular pixel response from that service).

The API view of this Manifest follows below. Note that:

* The manifest has extra properties like `slug`, `parent` etc.
* The image service on the canvas has a `paintedAsset` property, which shares fields in common with the IIIF-C [Asset](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/asset) but extends that resource to carry information about **the asset's relationship with the Canvas and the Manifest**
* The painted asset resource is repeated in the Manifest's `paintedAssets` list, which acts like the list of assets in a Space (space.images)[https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/space#images].
* Possibly the redundancy here may be avoid by just using a reference in one or other of these locations, however:
  * A Manifest might have a "painted" asset that belongs to another manifest (or no manifest, it may only be in a Space, or may be external altogether)
  * (?) The manifest might not use all of its "contained" assets in actual painting annotations on the canvas
* Not all canvases (or rather `painting` annotation bodies), will reference a "paintedAsset" - they could reference other external content resources.



```json
{
   "@context": [
       "http://tbc.org/iiif-repository/1/context.json",
       "http://iiif.io/api/presentation/3/context.json"
   ],
  "id": "https://api.iiif.library.leeds.ac.uk/iiif/manifests/t454knmf",
  "type": "Manifest",


  "slug": "ms-125",
  "usePath": true,
  "idInJson": "https://iiif.library.leeds.ac.uk/manuscripts/14th-century/ms-125",
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
                    "id": "https://images.library.leeds.ac.uk/iiif/5/MS_125_001",
                    "type": "ImageService3",
                    "profile": "level2",
                    "paintedAsset": {

                      "assetId": "https://api.dlcs.library.leeds.ac.uk/customers/2/spaces/76/MS_125_001",
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


                      "manifestId": "t454knmf",
                      "canvasId": "ae4b77wd",
                      "canvasOriginalId": null,
                      "canvasOrder": 0,
                      "choiceOrder": null,
                      "thumbnail": null,
                      "label": null,
                      "canvasLabel": { "en": [ "Canvas 1" ] },
                      "target": null,
                      "staticWidth": 6000,
                      "staticHeight": 9000                      
                      
                    }
                  ]

                },
                "target": "...(canvas-id)..."
              }
            ]
          }
        ],
        "thumbnail": [
          {"...": "..."}
        ]
      }
    ],
  "paintedAssets": [
    {
      "assetId": "https://api.dlcs.library.leeds.ac.uk/customers/2/spaces/76/MS_125_001",
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


      "manifestId": "t454knmf",
      "canvasId": "ae4b77wd",
      "canvasOriginalId": null,
      "canvasOrder": 0,
      "choiceOrder": null,
      "thumbnail": null,
      "label": null,
      "canvasLabel": { "en": [ "Canvas 1" ] },
      "target": null,
      "staticWidth": 6000,
      "staticHeight": 9000                      
      
    }
  ]
}
```

### Possible schema for Manifest

```sql
create table if not exists public.manifests
(
    id          varchar,
    slug        text,
    use_path    boolean,
    id_in_json  text,
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
| id_in_json            | The id of the Manifest last time it was persisted to S3 |
| parent                | id of parent collection (Storage Collection or IIIF Collection) |
| items_order           | Order within parent collection (unused if parent is storage) |
| space                 | Use this space to store assets for this Manifest (creates if non-existent; defaults to 0) **(see note 1)** |
| label                 | Derived from the stored IIIF Manifest JSON - a single value on the default language |
| thumbnail             | Not the IIIF JSON, just a single path or URI to 100px, for rapid query results |
| locked_by             | null normally; user id if being edited |
| created               | Create date |
| modified              | last updated |
| modified_by           | Who last committed a change to this Manifest |
| tags                  | Arbitrary strings to tag manifest, used to create virtual collections |
| simple                | One canvas_painting per canvas, no external assets, no non-null targets, no additional resources on canvas that are not known adjuncts or services |
| sheet                 | A Google Sheet or online Excel 365 sheet that the Manifest was created from, and can synchronise with. |


> ❓note 1: maybe this should default to minting a new space per manifest, to reduce naming collisions.
> That might be counterproductive as it inhibits moving.
> We should encourage asset IDs _after_ the `/<space>/` that are unique to the customer, e.g., include some aspect of the manifest in the asset id.
> There's no requirement that a manifest must use assets from a particular space, they could be from any space.


### The canvas_paintings table

This table stores the relationship between a Manifest in the manifests table above, and content resources. These content resources are _usually_ assets managed by the platform, but don't have to be.

This table is designed to be efficient for the 99% use case of one asset per canvas, filling that canvas - but nice to use for other content association scenarios encountered in IIIF. It's modelling four things:

* Canvases
* Painting annotations on the canvas
* Body of the painting annotation
* Choice items if body is a choice

> ❓TODO: adjuncts for Manifests and Canvases
> seeAlsos and annotations come from adjuncts which belong to ASSETS
> tbc how we do that for annos

We can project a Manifest from the information in this table, if that's all we have. But it deliberately falls far short of modelling all the things that canvases and annotations can have - these only exist in the JSON representation "on disk" (in S3). Updates to the Manifest from the JSON representation can be reflected back into this table. This table holds what we want to query on.

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
| canvas_id             | Canvases in Manifests always use a flat id, something like `https://dlcs.io/iiif/canvases/ae4567rd`, rather than anything path-based. If requested directly, IIIF-C returns canvas from this table with `partOf` pointing at manifest(s). `canvas_id` might **not be unique** within this table if the asset is `painted` in more than one Manifest |
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

> https://deploy-preview-2--dlcs-docs.netlify.app/manifest-view.html is an experiment to verify that tabular data like the above can be expressed first as a manifest (https://deploy-preview-2--dlcs-docs.netlify.app/manifest-builder/ms125_full-example.json) and then as a tabular HTML representation in the demo. Note the `paintedAssets` property in that example.

The `paintedAsset` property in the Manifest example is effectively a join of the assets table and the canvas_paintings table, and provides a mechanism to synchronise assets with their Manifest container at the same time the rest of the constructed Manifest JSON is constructed by a tool like iiif-builder.

> ❓If the canvases are "simple" can can be entirely round-tripped from the table alone, then synchronisation of a Manifest with the platform can _omit_ the `items` property altogether. This is the 99% use case for digitised material.
> TODO - canvases and resources will carry additional services and derivatives and renderings - adjuncts. For example, OCR data or IIIF annotations carrying full text. This simple synchronisation mechanism will still hold if the Manifest has adjunct policies and pipelines that determine what each canvas will carry.

You can update a whole Manifest's paintedAssets with additional `origin` and `deliveryChannels` info for processing, but in the 99% case this is just an asset with the additional ordering property.

> PaintedAsset is `asset` plus the `canvas_painting` properties, used instead of string1, number1 etc - although you can still set those old fields too - because it's still an Asset! A PaintedAsset can still have regular string and number metadata, as well as tags.

Because this approach exposes a `canvas_order` and `choice_order` property, you can use it do **insertions** of assets with simple synchronisation.



### Comparison with IIIF-C Spaces

To add assets to a manifest, you can POST batches for processing to a queue.

Therefore the Manifest has an endpoint:

* `(manifest_id)/queue`

This behaves just like a regular [queue](https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/queues) but does not require that incoming assets in batches declare the Manifest they are for.

The public facing API can also expose:

* `(manifest_id)/search`

... to provide IIIF Search API

> ❓This requires a separate RFC along with adjuncts and pipelines. 


And just as a space has assets, so does a manifest:

* `(manifest_id)/paintedAssets`

 
> ❓When using api.dlcs.io, manifest has /queue and /paintedAssets in extra service block, not present in public version.. dynamically added. Both api.dlcs.io/...manifest and dlcs.io/..manifest are proper manifests. 

* `(coll_id)/search`

The platform allows for IIIF Collections to expose a Search function _across manifests in the Collection_.

> ❓(This is a phase 2!) 



> ❓ We could add a new field `manifest_context` to asset, which is the ID of the Manifest that introduced the asset to the platform. This stays the same even if the asset is further used in other manifests. Usually it only gets used in one. This is a useful helper to build orphan deletion candidate lists.


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

Clients can choose whether to update manifests by POSTing Manifest JSON or by POSTing Platform API assets / paintedAssets, depending on the scenario. Any additional per canvas and hoc JSON must be persisted by sending IIIF Manifest JSON and letting the platform take care of merging that into the table. A Canvas can cayyy anything, and this is one of the main challenges with this approach.


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

... and then POST to `(@id)/paintedAssets` to add canvases..  like ../space/n/assets

Or

```json
{
    "@context": [
       // both contexts
    ],
    "id": null,  // 
    "type": "Manifest",
    "label": { },
    "paintedAssets": [
        {  } // DLCS painted Asset/Canvas_painting object, including optional delivery Channels, roles, origin etc
    ]
}
```

This way, **we can synchronise the manifest and its assets _together_**: "Here is a manifest, with its assets." You could create a manifest with initial assets like this. It comes back with a regular `items` property (although may not be fully populated with height and width yet). A batch will have been created. This batch could be retrieved from the queue.

A client could edit this resulting Manifest as JSON (in a text editor, or a visual Manifest Editor) and PUT it back, just as normal IIIF. The Platform is able to recognise its own assets and go back and forth between IIIF and paintedAsset representation.

A client can reference existing or external assets, including assets in other manifests (assets where there is no containment).

BUT a client cannot introduce an asset to the system from a purely IIIF represenation of _what it's going to look like - using the eventual public facing URL_ - there's not enough information (`origin`, `deliveryChannels` and so on are missing). An introduced, new Asset must come into the system as a "proper" Asset / paintedAsset.

> * The paintedAsset contains extra things used at ingest time but then reflected back in generated IIIF as order, auth services etc.
> * The IIIF Canvas also has any valid additional IIIF. 
> * The platform needs to be able to merge these.

The IIIF and paintedAssets are a Venn diagram, each can have some things the other doesn't, but the paintedAsset extra fields only relate to ingest (or reingest) information. they do not dictate what comes out in the public Manifest, except where consequences such as Auth services are present (because the `paintedAsset` had roles).

If instead you PUT a Manifest to its api URL, that incoming Manifest may have:

* Completely standard IIIF referencing both IIIF-C-managed and external resources. It can reference platform existing resources (assets) that weren't previously in the Manifest, or were in a different Manifest, or are existing assets in spaces. But you can't introduce an asset for the first time like this.
* Standard IIIF but with additional asset body attached to the content resource.
* A `paintedAssets[]` property providing the assets to be used, with or without the plain IIIF. These have the `order` property - not only to establish sequence (which could be from the array) but to allow interleaving with the IIIF.

Because we expose `paintedAssets` as a separate collection, you can have a cleanly separated Asset sync and IIIF Creation step. Most Canvases can be built entirely from the paintedAsset info and pipelines declared for the manifest. But even when that isn't the case, the robust IIIF <-> sync preserves additional information.

> ❓The MODEL behind the Manifest View in the portal is a manifest with both `items[]` and `paintedAssets[]` properties.


## Locking

In the current IIIF-C platform there is no concept of locking an asset for editing, or versioning an asset. This is fine because operations on assets are _individually_ short lived and atomic. But Manifests and IIIF Collections are potentially much more complicated, especially when those Manifests become content, with editorial, for exhibitions and so on. Even for simple use cases, the fact that the platform is a _repository_ for IIIF requires some degree of concurrency support for clients of the API.

An HTTP `GET` of a Manifest that includes an additional request for a **lock** in the form of an HTTP header (syntax TBC) returns an alt-location in a response header:

`.../<manifest-id>/locked` 

...that a client can make PUT calls to. When locked, there is another "working" manifest in S3 that handles updates from the API (even via a UI). This working Manifest only replaces the original on PUT to original URL, which unlocks and removes the locked version.

This transaction is only scoped to the Manifest; assets introduced while locked will still be added to the platform; if you then delete some and save those assets will be deleted too if they are belong to the manifest.

Locking is not required - it may be unnecessary overhead for a process like iiif-builder where other actors trying to edit the same resources is VERY unlikely. But the system will still prevent overwrites when when no locked was acquired, because use of eTags is mandatory (see below).

Any request for the Manifest while locked will return the original, with an HTTP header indicating that it is currently locked.

> ❓ What's happening in the canvas_painting table when the Manifest is locked? Are rows being updated or is the data being stored in a locked_canvas_painting table, or not even being stored at all other than implied in the JSON itself?

## Versioning

We can optionally save a timestamped copy of the previous version whenever a new version is saved.

Under s3 sub-key /versions

/versions/20240303144512  (1-second granularity like memento)


## ETags

A client must take note of the eTag returned with the response for an `api...` Manifest (or Collection), and send the same eTag on any PUT or POST that updates the Manifest.

> NB this is more fully developed in the CRKN prototype.

We still need to respect this when locked, still require client to send eTag on save: double protection. 

These two mechanisms (locking and eTags) are independent and locking is more useful for UIs like a Manifest Editor in a multi-user environment. You don't have to acquire a lock - but you run the risk of not being able to save your work if you don't, because someone might have updated the Manifest (and therefore generated a new eTag) behind your back.

A PUT with a valid eTag will create a new version without having to acquire a lock first (though will fail if it is actually locked at the time).

This allows human usage in a shared portal alongside machine usage through workflows.

Machines can do what they want without locking.

There is also API to kill a lock; and locks expire after a pre-configured timeout.




## Serving IIIF to the public

 - There is a Presentation API equivalent of the Orchestrator, although it never moves files around and is more purely a proxy.
 - IIIF Manifests and Collections are served by proxying S3, ideally with no DB query at runtime (like thumbs).
 - The IIIF-C API allows you to make a Manifest by solely submitting JSON, by solely adding assets, and by a combination of these two operations.
 - IIIF-C recognises its own assets in Manifest JSON, and therefore needs to understand where rewrite rules are in effect


### More on slugs, ids, paths, serving IIIF

Manifests, collections, storage collections have string IDs that are flat, and are stored in S3 under these IDs (with .json on the end)

* `s3://iiif-bucket/collections/ae45gh7e.json`
* `s3://iiif-bucket/manifests/t454knmf.json`

These ids are user supplied, from a minting service, or an ark service.

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

---

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