# Provisional data flows

This begins by looking at data flows that result in new manifests used on the existing special collections site.


## EPrints into Fedora

This assumes the existence of a custom EPrints migration script, that

 - can acquire an access token to consume the Preservation API
 - has read/write access to the S3 bucket (and sub key) that will be provided by the Preservation API

Begin with ePrints record? It has EMu IRN `123456` and ePrints ID `epxyz`.

The script calls the **Identity Service** - 

> "mint me an _archival group_ URI for the thing with EMu IRN 123456"

(Do we pass it both IDs? "FYI you can link 123456 and epxyx straight off the bat")

The Identity Service service returns a response that includes the Archival Group URI.

_What does its minted AG URI look like?_

(Need to tidy this up with the actual PID formats, here are some )

 - Simple but possibly naive - `/repository/emu/cat/123456`
 - Transformed (assume this more ARK-like) - `/repository/emu/cat/fgh-123456-sdf`
 - Opaque - `/repository/emu/cat/a6gr99n3`
 - Hierarchical - `/repository/emu/cat/a6gr99n3/tgb53pf4`
 - Bit of both -  `/repository/emu/cat/a6gr99n3/123456`

It doesn't exist yet but when it does, you can go and look at it at https://digipres-api.leeds.ac.uk/repository/emu/cat/123456 (or whichever of the above is used)

OPTIONALLY - if we want ID service to track this -

Script calls ID service - "mint me a _DEPOSIT ID_ for the thing with EMu 123456"
(we might not want to do this because the Preservation API can always tell us the deposits for an Archival Group)

Script then calls Preservation API:

```
POST /deposits
{
    "archivalGroup": "https://digipres-api.leeds.ac.uk/repository/emu/cat/123456",
    "archivalGroupName": "(E2) Research and papers : 2007-2011",
    "submissionText": "(optional note)"
}
```

The Preservation API recognises the URI as an EMu ID and validates it (this will happen for Born Digital human-driven work but that might be a function of the Preservation UI application rather than the API)

Script receives a Deposit object (with minted ID) that includes a `.files` property - the S3 working location.

Script uploads the contents of the EPrints object to that location (preserving folder structure)

QUESTION: 

 - does the script prepare its own new METS file? (like Goobi would)
 - ...or send the ePrints METS file as part of the payload?
 - ...or ask the Preservation API to make a METS file from the structure?

(the latter two are both possible and easier for the script!)

Script then tells the Preservation API to ingest directly:

```
POST /deposit/g5hm32pd/importjobs
{
    "id": "https://digipres-api.leeds.ac.uk/deposit/g5hm32pd/importjobs/diff"
}
```

(this is the shortcut "ingest immediately from a diff")

**The Preservation API now publishes a new Activity Stream event in its _Change Discovery API_**

https://iiif.io/api/discovery/1.0/

_(While this spec is an IIIF spec, we can also use it for any type of resource. This is like OAI/PMH (it even shares an author) but is simpler, easier, and JSON rather than XML)_

QUESTION

Preservation API publishes an event that says "A new Archival Group exists". How do we know that it should be IIIF-ified? There will be other preserved objects that aren't intended for IIIF. Maybe `forIIIF` is a formal property of the Preservation API's Deposit (but not the Archival Group itself, necessarily).

**IIIF-Builder** is a subscriber to that Activity Stream. The discovery service is not a message bus. IIIF Builder polls the change discovery endpoint at intervals to look for new work. This means that although IIIF Builder can be quite a simple Flask app, it needs some form of persistence to keep a record of what it has processed and when, so that it can react to new events.

IIIF-Builder acts on the new event.
It can see the Archival Group URI in the activity stream event. It asks the ID service:

"mint a IIIF Manifest URI for this Archival Group URL, and give me back all the other IDs you know"

(Internally Identity Service knows the EMu ID already and can use that to make decisions)

Later, one of these IDs will be the **Catalogue API URI** for this item. For now it might be the key-value simple API - but it's still a URI.

IIIF-Builder then requests the Archival Group from the Preservation API.

```
GET https://digipres-api.leeds.ac.uk/repository/emu/cat/123456
```

This gives it a listing of the contents _and their origin locations in S3_, including the METS file.

In a very simple world, IIIF-Builder could just use the file info from the Archival Group to build the Manifest. And this could be the simple initial EPrints case.

But we'll be using the METS file later because it can tell us more that may have been added in Goobi or the Preservation UI:
 
 - logical structure
 - right statements
 - access conditions
 - any additional technical metadata we might want to surface in the IIIF (not much probably)

IIIF-Builder loads the METS file and uses it to build a IIIF Manifest - but instead of constructing the Canvases manually, it sends the manifest with a payload of `PaintedResource` objects:

https://deploy-preview-2--dlcs-docs.netlify.app/api-doc/iiif#paintedresource

Example:
https://github.com/dlcs/iiif-presentation-tests/blob/8e848de2c6a2437bdc1243a4c692469c6c17ce77/tests/apiscratch/t0070---managed-asset-manifests.spec.ts#L24

each `paintedResource.asset` property includes the `origin` S3 URI that IIIF-Builder can see in the ArchivalGroup resource.

It also calls the Catalogue API (or pseudo catalogue API) URI it learned from the identity service

```
GET "https://explore.library.leeds.ac.uk/imu/utilities/getIIIFData.php?irn=123456"
```

It uses this data to build up the IIIF `label` and `metadata` properties.

Now we have a IIIF Manifest with the right descriptive information, but without an `items` property. It has a `paintedResources` property instead, which is used to ingest new assets to IIIF-CS easily.

Now it PUTs that Manifest to the URI provided by the identity service:

```
PUT /library/xyz/123456
{
    "type": "Manifest",
    "label": { "en": [ "(E2) Research and papers : 2007-2011" ]},
    "metadata": [ .. ],
    "provider": {
        // boilerplate Leeds agent resource
    },
    "rights": ...
    "paintedResources": [
        { 
            "asset": {
                "origin": "s3://fedora-bucket/initial/3hf29f7y2n9rfy2n94ry6n29yrc6b2952/123456/v1/objects/page-1.tiff"
            }
        }
    ]
}
```

This returns with an "Accepted" HTTP response, and the returned manifest has an `ingesting` property with some information that can be used to report progress.

_If it wants to_ IIIF Builder can poll this until complete. Or it could forget about it.

When it is complete, IIIF-CS will publish an event to _its_ activity stream (which for IIIF-CS is now a pure IIIF Change Discovery endpoint, and may even be public)

QUESTION

IIIF-Builder could publish its own change discovery stream. But it probably doesn't need to; subscribers can listen to IIIF-CS Change Discovery.

How does the web site know about the Manifest?

The web site could subscribe to the activity stream and build up its own map of which EMu IRNs have manifests.
The web site could on-demand ask the identity service for Manifest IDs.

(Glossed over in this walkthrough is the distinction between public IIIF Manifest URIs, which are vanilla IIIF 3.0, and "API" Manifests URIs, which offer/can receive extra information (including paintedResources)). The ID service will need to have both URIs, although the IIIF-CS Presentation API allows you to learn one from the other.


I could now ask the ID service:
"show me all you know about EMu 123456" and it would give me back:

 - An EMu ID
 - An Archival Group URI
 - A Deposit ID (or more than one) (optional)
 - A IIIF Manifest URI
 - The Catalogue API URI (or provisional version)


## Digitised from scratch

This is the process for born digital, starting with "I want to preserve the files for EMu IRN 567890" and then "I want 567890 to be available as IIIF"

An archivist goes to the Preservation UI in a browser. While ad-hoc archival groups can be created anywhere in the structure, the UI has a special process for EMu. The "New Deposit" is a drop-down menu that offers "from EMu". The archivist picks this one and the UI shows them a dialogue box that asks for the EMu IRN or classmark (i.e., it accepts `652832` or `MS 2067/B/2/6/2`).

The Preservation UI asks the Identity service for an Archival Group URI (as above) for this identifier. If it already exists then this becomes an EDIT operation - let's assume it's new.

The Preservation UI then goes to EMu API directly (possibly the Catalogue API later) and collects some information, most obviously the title which will be both the name of the archival group, and added to the METS file. Any other rights information or data we want from EMu in the METS can be gathered here. 

The Preservation UI (and API) create and manage a METS file for this object, and the UI of the deposit page is a visual representation of this METS file structure.

The UI then asks the Preservation API to create a deposit for this archival group.

As the archivist uploads files, the Preservation UI adds them to the METS file. This is the manual equivalent of the EPrints script pushing the EPrints files into the deposit working area.

Once the assembly of the Archival Group is complete, it is submitted as in the above example and the rest of the workflow is the same.


## Alternative paths

Objects involving many files, or otherwise complex structures or diverse material, will begin their workflow in BitCurator. Initial work is done here and ends up with a BagIt bag folder structure being created.

Once done the archivist uploads the whole BagIt structure to a staging area using either an SFTP client, or a direct S3-supporting file transfer client (they will both end up in a bucket). This crucially does not go via the Preservation Web UI with potentially huge file transfers over HTTP.

Once done, the archivist goes to the Preservation UI and creates a new Deposit "From BagIt", providing the root S3 location (or FTP location, which the UI will transform into the S3 location). On the server the Preservation API interrogates the BagIt and creates a METS file in the Deposit, transferring over the data files but not necessarily the BagIt artifacts and other forensic analysis tool outputs. The API might use these outputs, but convert their information into data that can go into the METS file.

The end result is a Deposit with a METS file and the full contents, which can then process as the earlier example above.