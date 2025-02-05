# Containers and Binaries

There are two distinct scenarios for classes that represent files and folders across the system.

The first are _resources_ returned by an HTTP API. They are information objects; they are navigable structures.

- Containers and Binaries in Fedora
- Containers and Binaries in the Storage API
- Containers and Binaries in the Preservation API

The resources live at URIs that represent their stored, permanent locations.
When we browse the storage API, or Preservation API via the web user interface, we are interacting with these resources.

The second are file and folders _in transit_ or potentially in transit. Files that have been exported, or files that have been assembled to be imported. These have real **location** on disk or in S3, places we can put them or read them from. 

There is a little overlap between these concepts, in that an API resource can include a reference to a location on a filesystem or S3 that _corresponds_ to the API resource. This is how the Storage API provides the `origin` to the DLCS and other callers.


### Problems with the Prototype models

Container and Binary classes know about URIs that are not in their scope; e.g., you can see a Fedora URI and a Storage API URI in the Storage API response.

Callers of one API should have no knowledge of the deeper API; callers of Preservation API should have no idea about Storage API and callers of Storage API shouldn't see traces of Fedora.

### Questions

The second kind of resource should be resuable across the entire codebase. In the prototype we have BinaryFile and ContainerDirectory that are actually in the Fedora csproj but are used by the Preservation API (clearly wrong).

The first kind of resource _may_ be reusable, and certainly can have more common ground than at present.

Possibly base classes that are extended in different contexts (e.g., only the Storage API version gets `origin`).

### Outcome

`Container`, `ArchivalGroup` and `Binary` are classes used throughout the codebase when we are sending resources for preservation, or receiving them from Preservation. They live here:

https://github.com/uol-dlip/digital-preservation/tree/main/src/DigitalPreservation/DigitalPreservation.Common.Model

`WorkingDirectory` and `WorkingFile` are used when we are interacting with files and directories on disk (or more likely, in S3). They live here:

https://github.com/uol-dlip/digital-preservation/tree/main/src/DigitalPreservation/DigitalPreservation.Common.Model/Transit

The name _DigitalObject_ has been dropped. Better to use `ArchivalGroup` everywhere even though it's not quite as obvious what it is to newcomers. It avoids confusion and allows someone who knows Fedora to understand the intent of the UI (for example).