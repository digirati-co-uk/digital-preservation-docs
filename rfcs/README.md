# Requests for comments

1. [001 What is stored in Fedora?](001-what-is-stored-in-fedora.md)
1. [002 The Storage API](002-storage-api.md)
1. [003 The Preservation API](003-preservation-api.md)
1. [004 IIIF Manifests and Collections](004-storing-iiif-manifests-and-collections.md)

* Fedora - linked data platform, Vanilla Fedora API.
* Storage API - Sits in front of Fedora. API to organise a repository with Containers (folders), store versioned Archival Groups, that contain Binaries (and Containers).
* Preservation API - Deposits that create Digital Objects. Requires METS files that _describe_ the Digital Object, providing at least checksums, original filenames and format information.

The Storage API is Fedora-facing - it provides a wrapper around Fedora. The Preservation API is "application-facing" - it provides APIs suited to building digital preservation applications and workflows, that explicitly use METS files to describe contents.  The Storage API exposes the underlying OCFL model behind Fedora 6, whereas the Preservation API hides it. Consuming applications call the Preservation API over HTTP, the Preservation API calls the Storage API over HTTP, the Storage API calls Fedora over HTTP. 

Some applications in DLIP, like IIIF-Builder, have the privilege of calling the Storage API directly. IIIF-Builder uses it to find the origin S3 key of assets.

The Storage API has no state of its own, it is a proxy to Fedora.
But the Preservation API keeps track of things in a (relatively simple) database. It has more "model".

