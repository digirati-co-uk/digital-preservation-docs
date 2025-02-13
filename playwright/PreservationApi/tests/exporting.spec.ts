import {expect, test} from '@playwright/test';
import { createArchivalGroup } from './quick-prep.spec'
import {getS3Client, listKeys, uploadFile, waitForStatus} from "./common-utils";
import {ListObjectsV2Command} from "@aws-sdk/client-s3";

// Create a new deposit by exporting a version


test.describe('Export an existing Digital Object and make changes to it, then create a new version in Digital Preservation', () => {


    test('exporting-to-edit-mets', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);

        // Background prep
        console.log("Starting condition is a Preserved Digital Object in the repository - we'll make one for this test");
        const archivalGroupUri = await createArchivalGroup(request, baseURL);
        console.log("Created " + archivalGroupUri);

        // The demonstration
        // Assumes we no longer have the original deposit that made the digital object in the first place
        console.log("An hour later, or 10 years later, we want to take a look at the files and possibly edit them.");
        console.log("We could ask for a specific version, but we'll omit the version property to get the most recent (which should be v1 here)")
        const exportResp = await request.post('/deposits/export', {
            data: {
                archivalGroup: archivalGroupUri // This object is actually a deposit; see new version
            }
        });
        const exportDeposit = await exportResp.json();
        expect(exportDeposit.files).toMatch(/s3:\/\/.*/);
        console.log("The files for " + archivalGroupUri + " will be placed under " + exportDeposit.files);
        console.log("But we need to wait for the export to finish! It might take a long time");
        await waitForStatus(exportDeposit.id, "new", request);

        const s3Client = getS3Client();
        await listKeys(s3Client, exportDeposit.files);

        console.log("We realised we missed a page all those years ago, so we need to add a new image and also modify the METS file.")
        const sourceDir = 'samples/10315s-add-jpg/';
        const files = [
            '10315.METS.xml',
            'objects/IbqX6-fA.jpg'
        ];
        for (const file of files) {
            await uploadFile(s3Client, exportDeposit.files, sourceDir + file, file)
        }

        console.log("Now generate an importJob from a diff");
        const diffJobGeneratorUri = exportDeposit.id + '/importjobs/diff';
        console.log("GET " + diffJobGeneratorUri);
        const diffReq = await request.get(diffJobGeneratorUri);

        const diffImportJob = await diffReq.json();
        console.log(diffImportJob);
        console.log("----");
        expect(diffImportJob).toEqual(expect.objectContaining({
            originalId: diffJobGeneratorUri,
            archivalGroup: archivalGroupUri,
            deposit: exportDeposit.id,
            sourceVersion: expect.objectContaining({
                ocflVersion: 'v1'
            }),
            containersToAdd: [],
            containersToDelete: [],
            binariesToDelete: [],
            binariesToAdd: expect.arrayContaining(
                [
                    expect.objectContaining({id: expect.stringContaining('/objects/IbqX6-fA.jpg')})
                ]),
            binariesToPatch: expect.arrayContaining(
                [
                    expect.objectContaining({id: expect.stringContaining('/10315.METS.xml')})
                ]),
        }));
        expect(diffImportJob.binariesToAdd.length).toEqual(1);

        // ### API INTERACTION ###
        const executeJobUri = exportDeposit.id + '/importjobs';
        console.log("Now execute the import job...");
        console.log("POST " + executeJobUri);
        const executeImportJobReq = await request.post(executeJobUri, {
            data: diffImportJob
        });
        let importJobResult = await executeImportJobReq.json();
        console.log(importJobResult);
        expect(importJobResult).toEqual(expect.objectContaining({
            type: 'ImportJobResult',
            originalImportJob: diffJobGeneratorUri,
            status: 'waiting',
            archivalGroup: archivalGroupUri
        }));
        console.log("----");

        console.log("... and poll it until it is either complete or completeWithErrors...");
        await waitForStatus(importJobResult.id, /completed.*/, request);
        console.log("----");

        // Now we should have an UPDATED digital object in the repository:

        // ### API INTERACTION ###
        console.log("Now request the digital object URI we made earlier:");
        console.log("GET " + archivalGroupUri);
        const digitalObjectReq = await request.get(archivalGroupUri);

        expect(digitalObjectReq.ok()).toBeTruthy();
        const digitalObject = await digitalObjectReq.json();
        console.log("We expect to see two versions available in this object")
        console.log(digitalObject);

        expect(digitalObject).toEqual(expect.objectContaining({
            id: archivalGroupUri,
            type: 'ArchivalGroup',
            name: '[Example title]', // This will have been read from the METS file  <mods:title>
            version: expect.objectContaining({ocflVersion: 'v2'}),  // and we expect it to be at version 2
            versions: expect.arrayContaining(
                [
                    expect.objectContaining({ocflVersion:'v1'}),
                    expect.objectContaining({ocflVersion:'v2'})
                ]
            ),
            binaries: expect.arrayContaining(
                [
                    // and it has a METS file in the root
                    expect.objectContaining({id: expect.stringContaining('10315.METS.xml')})
                ]),
            containers: expect.arrayContaining(
                [
                    // and an objects folder with 4 JPEGs in it
                    expect.objectContaining(
                        {
                            type: 'Container',
                            name: 'objects',
                            binaries: expect.arrayContaining(
                                [
                                    expect.objectContaining({id: expect.stringContaining('/objects/372705s_001.jpg')}),
                                    expect.objectContaining({id: expect.stringContaining('/objects/372705s_002.jpg')}),
                                    expect.objectContaining({id: expect.stringContaining('/objects/372705s_003.jpg')}),
                                    expect.objectContaining({id: expect.stringContaining('/objects/372705s_004.jpg')}),
                                    expect.objectContaining({id: expect.stringContaining('/objects/IbqX6-fA.jpg')}),
                                ]
                            )
                        }
                    )
                ])
        }));
    })
});