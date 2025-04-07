import {test, expect, APIRequestContext} from '@playwright/test';

import { XMLParser } from 'fast-xml-parser';
import {
    CatalogueApiClient,
    IdentityServiceClient,
    IdentifierTypes,
    getBoilerPlateManifest
} from "./iiif-builder-boilerplate";

const iiifCsCredentials = "<dummy-api-key-and-secret-for-IIIF-CS-auth-token>";
const preservationApiBearerToken = "<dummy-preservation-api-token>";  // not a real token obvs...

// https://github.com/uol-dlip/docs/blob/begin-formal-documentation/rfcs/110-provisional-data-flows.md


test('iiif-builder-demonstration', async ({request}) => {

    const preservationActivityStream = "https://preservation-dev.dlip.digirati.io/activity"

    let activityFromPreservationStream: any;
    let archivalGroupUri: string;
    let archivalGroup: any;
    let parsedMets: any;
    let publicManifestUri: string;
    let apiManifestUri: string;
    let apiManifestFlatId: string;
    let catalogueUri: string;
    let manifest: any;
    let descriptiveMetadata: any;

    await test.step("Inspect Preservation Activity Stream", async () => {

        // https://iiif.io/api/discovery/1.0/
        // IIIFBuilder reads the Preservation API Activity Stream back to the point
        // it last read (e.g., 10 minutes ago). It finds one new Event in the stream.
        const streamHomeResponse = await request.get(preservationActivityStream, {
            headers: {
                "Authorization": `Bearer ${preservationApiBearerToken}`,
                "Identity": "iiif-builder"
            }
        });
        const streamHome = await streamHomeResponse.json();
        // assume that since last visit no new pages have been added,
        // so we only need to get the last page and see what's been added to THAT
        const lastPageResponse = await request.get(streamHome.last.id, {
            headers: {
                "Authorization": `Bearer ${preservationApiBearerToken}`
            }
        });
        const lastPage = await lastPageResponse.json();

        // and let's assume that there is only one new activity since our last visit:
        activityFromPreservationStream = lastPage.orderedItems[97];
        // we'll fake it:
        activityFromPreservationStream = {
            "type": "Create",  // Or could be an Update - see later for what we would do differently
            "object": {
                "id": "https://preservation-dev.dlip.digirati.io/repository/eprints-migration/a6gr99n3",
                "type": "ArchivalGroup"
            },
            "endTime": "2025-02-05T00:00:00Z"
        }
        archivalGroupUri = activityFromPreservationStream.object.id;
    });

    await test.step("Fetch Archival Group", async () => {
        // Assume that IIIF-Builder has valid credentials for the Preservation API,
        // and that it keeps its JWT Bearer Token refreshed using its client id and secret.
        const archivalGroupResponse = await request.get(archivalGroupUri, {
            headers: {
                "Authorization": `Bearer ${preservationApiBearerToken}`
            }
        });
        archivalGroup = await archivalGroupResponse.json();
    });

    await test.step("Load METS XML", async () => {
        // IIIF-Builder could inspect the archival group and find the METS file, but
        // there is also a query parameter (?view=mets) which returns the METS XML for an Archival Group directly.
        // This is preferred as it ensures the METS is the same one the Pres API has been working with.
        const metsResponse = await request.get(archivalGroupUri + "?view=mets", {
            headers: {
                "Authorization": `Bearer ${preservationApiBearerToken}`
            }
        });
        const metsXmlString = (await metsResponse.body()).toString();
        const parser = new XMLParser();
        parsedMets = parser.parse(metsXmlString);
    });

    await test.step("Get the Manifest URI and the catalogue API URI", async () => {
        // cheating slightly, will come back and expand when we know what this API looks like
        const idService = new IdentityServiceClient();
        publicManifestUri = await idService.getIdentifier(archivalGroupUri, IdentifierTypes.IIIFManifest);
        catalogueUri = await idService.getIdentifier(archivalGroupUri, IdentifierTypes.CatalogueApi);

        // discussion - we could ask the identity service for both
        // publicManifestUri and apiManifestUri (the internal, flat, admin URI)
        // and it could give completely different looking URIs.

        // Here I am assuming that the identity service is only dishing out
        // the public URI, and as long as we are consistent we can forge
        // our own internal, flat ID. We could also let IIIF-CS mint it,
        // but I think it's more useful to be able to recognise it.

        // You can always find one from the other using the IIIF-CS API
        const url = new URL(publicManifestUri);
        apiManifestFlatId = url.pathname.substring(1).replaceAll('/', '_');
        apiManifestUri = `https://${url.hostname}/2/manifests/${apiManifestFlatId}`;
        // e.g., https://iiif.leeds.ac.uk/2/manifests/eprints_a6gr99n3
        // /2/ is the "customer" which we will use to partition dev, test, prod etc
    });

    await test.step("Get descriptive metadata", async () => {
        // cheating slightly, will come back and expand when we know what this API looks like
        const catalogue = new CatalogueApiClient();
        descriptiveMetadata = await catalogue.getRecord(catalogueUri);
    });

    await test.step("Start to build the Manifest", async () => {
        // In this simplistic IIIF Builder, there will be no difference in this step
        // whether it's a Create or an Update - we just prepare the Manifest as it should be,
        // and then save it. Doesn't matter whether that means overwriting an existing one.

        // This looks like a regular IIIF Manifest, and will appear as one on the public
        // URI we got from the ID service. But we are using some extra fields.
        // We are going to PUT this to its "flat" API path, which will remain constant
        // even if the public _hierarchical_ URI changes (e.g., if the public
        // URL structure is re-arranged).
        manifest = getBoilerPlateManifest();
        manifest.publicId = publicManifestUri;
        // We are not specifying the id property here, see later when we PUT this to manifestUri
        manifest.label = { "en": [ descriptiveMetadata.title ] };
        manifest.metadata = [
            {
                "label": { "en": [ "author" ] },
                "value": { "en": [ descriptiveMetadata.author ] },
            }
        ];
        // and so on... even:
        manifest.seeAlso = [
            {
                "id": descriptiveMetadata.id,
                "type": "Dataset",
                "label": "Catalogue API record"
            }
        ];
    });

    await test.step("Add the assets! (images in this case)", async () => {
        // Note that there is no items[] in our manifest.
        // For IIIF-Builder MVP we are going to do EVERYTHING with paintedResources.

        // get a list of physical files from the mets XML
        // THIS IS VERY FAKE, will update when I have some real METS here
        // This gets the relative path, content type and display label FROM METS for the assets in order
        const metsSourcePhysicalFiles = extractFileInfo(parsedMets);

        // Now is the most important part!
        // In our initial iiif-builder flow, we will ONLY use `paintedResources` and never send
        // the Manifest with an `items` property. This means that IIIF-CS will generate and manage
        // the IIIF Canvases. This means we can't put arbitrary properties on the Canvases.
        // But we can do enough to cover basic requirements; the canvasPainting resource
        // allows us to give the canvas a label. It also allows to construct canvases with
        // Choice annotation bodies, and multiple images on the same Canvas, and targets that
        // are not the whole Canvas. These extras are not needed for EPrints and are not shown here.

        // The following code constructs the Manifest paintedResources as we want them to be,
        // regardless of what's there already (if anything). In the step after this we will distinguish
        // between assets that we want to be there and don't need any further work, and assets
        // that we want to re-process (most likely because the file at a particular relative path changed in
        // an update to an archival group).
        manifest.paintedResources = [];
        for (let i = 0; i < metsSourcePhysicalFiles.length; i++) {
            const metsInfo = metsSourcePhysicalFiles[i];

            // Now we use the relative path from METS to obtain the S3 origin from the Archival Group *Storage Map*
            // There are two ways of obtaining the origin - the underlying S3 URL from which IIIF-CS will
            // fetch the image. The first involves concatenating the Archival Group root origin with the file path
            // within the OCFL object:
            const origin = `${archivalGroup.origin}/${archivalGroup.storageMap.files[metsInfo.xlink].fullPath}`

            // The second mechanism would involve traversing the Container hierarchy, following
            // the path given by metsInfo.xlink. This gives you the S3 URI directly (the origin property
            // of the binary at the end of the path) but is more code otherwise.

            // See t0300-iiif-builder-boilerplate.ts for a sample archival group, to see how the
            // above line works.
            // (the large object at the end of the file).

            manifest.paintedResources.push({
                canvasPainting: {
                    // canvasId is optional but gives iiif-b more control. IIIF-CS will mint its own otherwise.
                    canvasId: getCanvasIdFromFilePath(apiManifestFlatId, metsInfo.xlink),
                    canvasOrder: i,                      // optional, will use array order otherwise
                    label: { "en": [ metsInfo.label ]}   // e.g., page numbers... e.g., "xvii", "37r", etc.
                },
                asset: {
                    id: metsInfo.xlink.split('/').pop(),       // use the file name as the ID. Will be scoped to the manifest.
                    mediaType: metsInfo.contentType,
                    origin: origin
                }
            })
        }
    });


    await test.step("Decide what needs to be reingested and Save", async () => {

        // The publicManifestUri obtained earlier from the identity service is the public URI.
        // Our manifest is an "API" manifest; it uses `paintedResources` and we
        // are sending it in as the authed user with the extras header.

        // We are PUTting it to the Flat API endpoint, using the apiManifestUri that
        // we created earlier. 
        
        // Alternatively we might get this ID from the identity service.

        // At this point we don't know whether the Manifest exists.
        // Although if the activity was a "Create" then almost certainly it won't.
        // But if this code is to handle both scenarios, we need to know whether the Manifest
        // exists (we're overwriting it) or not (we're creating it). We won't be able to do the former
        // without a valid ETag.

        const existingManifestResponse = await request.get(publicManifestUri, {
            headers: {
                "Authorization": `Basic ${iiifCsCredentials}`,
                "X-IIIF-CS-Show-Extras": "All"
            }
        });
        let eTag : string | null = null;
        if(existingManifestResponse.status() == 404){
            // all good, it doesn't exist
        } else if(existingManifestResponse.status() == 200){
            // also good. It exists, so we need an eTag. But it's not "in flight" (202)
            eTag = existingManifestResponse.headers()["ETag"];
            // BUT we need to say what actually needs changing, if anything
            const existingManifest = await existingManifestResponse.json();
            updateIngestStatus(existingManifest, manifest);
        } else {
            // NOT GOOD - we can't edit this right now for whatever reason
            // TODO - deal with other status codes such as 202, 401, 403
        }

        const putHeaders : any = {
            "Authorization": `Basic ${iiifCsCredentials}`,
            "X-IIIF-CS-Show-Extras": "All"  // QUESTION: DO we need that on a POST?
        };
        if(eTag){
            putHeaders["If-Match"] = eTag;
        }

        const initialPutResponse = await request.put(apiManifestUri, {
            headers: putHeaders,
            data: manifest
        });

        // The above is the actual save.
        // What follows in this step is some playwright assertions to demonstrate
        // some IIIF-CS behaviour.

        // expect(initialPostResponse.status()).toEqual(201); // HTTP Created
        // This could only happen if it's a new Manifest with no assets - so can be created synchronously.
        // which?
        expect(initialPutResponse.status()).toEqual(202); // HTTP Accepted
        // 200 also acceptable for update that needs no processing
        // 200 and 201 both treated the same in this code.
        // Is it accepted here even if it's new?
        // I think so; later we check for 202 to see if it's in flight, so it can't be 201 and then 202 later.
        // Or can it?

        // If for some reason someone had snuck in and edited the manifest after we acquired the ETag
        // above, then this status would be 412 - Precondition failed.
        // That is highly unlikely for iiif-builder here, but the eventual version of iiif builder
        // must handle it.

        // Now there is no ETag, because it's in-flight.
        expect(initialPutResponse.headers()["ETag"]).not.toBeDefined(); // see t0071 for more details
        const newlyCreatedManifest = await initialPutResponse.json();

        expect(newlyCreatedManifest['items']).toHaveLength(3);
        expect(newlyCreatedManifest).toEqual(expect.objectContaining({
            "id": apiManifestUri,  // <== ########## FLAT ##############
            "type": "Manifest",
            "label": manifest.label,
            "publicId": publicManifestUri,                          // <== ###### HIERARCHICAL ##########
            "ingesting": expect.objectContaining({
                "finished": 0,
                "total": 3
            })
        }));

        // Try to obtain the manifest again immediately - it is "in flight"
        // This GET can be made with either apiManifestUri or publicManifestUri

        // GET apiManifestUri will return a 200 or 202 and show the in-flight manifest
        // GET publicManifestUri will return a 200 if this is an update, if it's a create and not yet finished it'll be 404
        const inFlightManifestResp = await request.get(apiManifestUri, {
            headers: {
                "Authorization": `Basic ${iiifCsCredentials}`,
                "X-IIIF-CS-Show-Extras": "All"
            }
        });
        expect(inFlightManifestResp.status()).toEqual(202); // 202 on GET is different from 202 on POST
        // It has been accepted (i.e., was accepted at some point previously) but it is still running
        // No ETag because it is not in a state that can be picked up for editing; it is being processed.
        expect(inFlightManifestResp.headers()["ETag"]).not.toBeDefined(); // see t0071 for more details

    });


    await test.step("Optional - poll for completion", async () => {
        // Now we wait...
        // We might not care to wait for this - we're not going to do anything else when it finishes.
        // IIIF-CS will publish an event to its Activity Stream for the Manifest.
        await waitForIngestingFalse(apiManifestUri, request);
    });

});


// helpers


function getCanvasIdFromFilePath(manifestFlatId: string, path: string) {
    return `${manifestFlatId}_${path.replace('/', '_')}`;  // this isn't actually a bad approach
}


function extractFileInfo(parsedMets: any) {
    console.log(parsedMets);
    // I'm not really going to traverse the parsed METS here, pretend we got this out of it.
    // This is what we are initially interested in from METS but later we can pull structure
    // (for Ranges), Access Conditions, Rights statements and more.
    return [
        {
            xlink: "objects/images/page1.tiff",
            contentType: "image/tiff",
            label: "1"
        },
        {
            xlink: "objects/images/page2.tiff",
            contentType: "image/tiff",
            label: "2"
        },
        {
            xlink: "objects/images/page3.tiff",
            contentType: "image/tiff",
            label: "3"
        }
    ];
}

function updateIngestStatus(existingManifest: any, newManifest: any) {

    // You could leave the IIIF-CS to decide whether or not to reingest a re-supplied asset.
    // But it plays it quite safe and may reingest things that haven't changed.

    // If an asset is repeated (appears more than once) it's OK as Array.find() only returns
    // the first, and we only need to tell it to reingest once.

    const seenIds = [];
    for (const newPaintedResource of newManifest.paintedResources) {
        if(seenIds.indexOf(newPaintedResource.asset.id) == -1){
            seenIds.push(newPaintedResource.asset.id);
            const existingPaintedResource = existingManifest.paintedResources.find(
                pr => pr.asset.id == newPaintedResource.asset.id);
            if(!existingPaintedResource){
                newPaintedResource.reingest = true;
                continue;
            }
            if(existingPaintedResource.origin != newPaintedResource.origin){
                newPaintedResource.reingest = true;
            }
        }
    }
}

async function waitForIngestingFalse(uri: string, request: APIRequestContext){
    await expect.poll(async () => {
        const resp = await request.get(uri, {
            headers: {
                "Authorization": `Basic ${iiifCsCredentials}`,
                "X-IIIF-CS-Show-Extras": "All"
            }
        });
        const respObj = await resp.json();
        if(respObj['ingesting']){
            return true; // there is an object here
        }
        return false;
    }, {
        intervals: [2000], // every 2 seconds
        timeout: 60000 // allow 1 minute to complete
    }).toBe(false);
}
