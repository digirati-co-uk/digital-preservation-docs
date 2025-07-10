# Structure: Archival, Digital Object, Preservation

Different domains offer different _mechanisms_ for organisation:

* At the Archival description layer we have archival hierarchy - series, items, files, parts etc.
* At the Preservation layer we have repository structure (Containers above the level of Archival Groups, really just used for organising), Archival Groups which are the unit of versioning, and within Archival Groups, arbitrary Containers and Binaries.
* At the IIIF layer we have Collections, Manifests and [Ranges](https://iiif.io/api/presentation/3.0/#54-range).

In between these layers we have (or could have) 

 - program or process logic that decides when to create an Archival Group and what it corresponds to (sits between EMu and Preservation UI or API)
 - program or process logic that creates a rich(er) logical `structMap` in a METS file at the root of the Archival Group
 - program or process logic that assigns rights and access information to elements of the structMap (which might just be a single assertion at the root or might go into granular detail)
 - program logic that converts the information in Catalogue records, Archival Group structure in METS files and rights or access assertions in METS files into IIIF Collections, Manifests and Ranges, and assigns roles mapped from access conditions to the individual assets (content resources such as images, audio and video, or in fact any document) in IIIF-CS


 Simple mapping is:

 one Archival Item in EMu => One Archival Group in preservation => One IIIF Manifest with uniform access and rights across all its content

 Here's an article that touches on some of these issues:
 https://medium.com/digirati-ch/web-pages-and-viewers-meet-things-with-content-b0755e644ea6


Key things to remember:

* The IIIF Manifest is the unit of **distribution** of the digital objects. You can't serve up part of a Manifest in isolation, but you can load a viewer focussed on that part, and you could design user interfaces to do more interesting things with parts of Manifests.
* The IIIF Range is an _optional_ unit of **structure** within a Manifest, that could correspond to distinct units of archival description within the same Manifest (see the stomachs example in the article linked above).
* Archival description has many levels that may or may not correspond neatly or consistently to what makes sense as a unit of digital distribution. This is not a bad thing, it's just how it is. In one series a single record might terminate the hierarchy on a whole physical box of papers, in another series a single descriptive record might align with a fragment of one piece of paper.
* The Archival Group is the unit of versioning as well as of preservation. 
* The METS file could hold the relationship between EMu records and parts (logical structMap elements) of the preserved object, down to the level of individual binaries _or even below_ and iiif-builder could use this information 
* More generally, the METS is an intermediary that bridges the information from EMu, from digitisation workflow in Goobi and from human decisions in the Presentation UI to the eventually produced IIIF Collections, Manifests and Ranges. We don't directly map archival hierarchy to IIIF and this relationship is not known _in either direction_ at the preservation layer; it's iiif-builder that encodes our rules about how we map from METS to IIIF, and these rules could change and produce different IIIF outputs without the source information changing.

All this is immensely flexible, we can do whatever we want.

Whether we _should_ is another matter; we might end up tying ourselves in knots with horribly complex workflows and non-obvious relationships between descriptions and *things*, that may be confusing to users (both staff and public). Ideally iiif-builder's business logic simply asserts what IIIF should exist, statically from reading a METS file, and doesn't have complex logic for patching and rearranging existing IIIF; it's simpler if it always _remakes_ the IIIF that it thinks should exist. It's up to IIIF-CS to be clever enough about not unnecessarily reprocessing images and video, etc.


* The identity service is key to this; I think that any element in a METS logical structMap should be known to and identified by the identity service, and that element is converted by iiif-builder to a Range when it creates a Manifest, with a shared identity, and that the identity service can *resolve* these arbitrary parts. So if you have EMu AA/BBB/789/3/2, the identity service can tell you "that is the IIIF Range https://iiif.library.leeds.ac.uk/presentation/ranges/h6t44mm3 in IIIF Manifest https://iiif.library.leeds.ac.uk/presentation/ranges/qqd9km2b" and a user experience on the collections site could load that manifest and focus on that Range, just from the EMu id.



Clearly further detailed description of parts within an already described object is a possibility, but are there scenarios where things would break?