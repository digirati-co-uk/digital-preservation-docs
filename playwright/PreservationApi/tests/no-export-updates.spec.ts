import {expect, test} from '@playwright/test';
import { createArchivalGroup } from './quick-prep.spec'
import {getS3Client, getShortTimestamp, uploadFile, waitForStatus} from "./common-utils";

test.describe('Update an Archival Group without exporting anything first', () => {


    test('no-exporting', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);

        // Background prep
        console.log("Starting condition is a Preserved Digital Object in the repository - we'll make one for this test");
        const archivalGroupUri = await createArchivalGroup(request, baseURL);
        console.log("Created " + archivalGroupUri);

        console.log("Create a new Deposit - NOT an export:");
        console.log("POST /deposits");
        const newDepositResp = await request.post('/deposits', {
            data: {
                archivalGroup: archivalGroupUri,
                submissionText: "Creating a new deposit to demonstrate updates without exporting"
            }
        })
        const newDeposit = await newDepositResp.json();
        console.log("New Deposit created:");
        console.log(newDeposit);
        console.log("----");

        console.log("Now upload the changed file - just the METS and not 5GB of tiffs!")
        const s3Client = getS3Client();
        await uploadFile(s3Client, newDeposit.files, 'samples/10315s-tweaked-METS/10315.METS.xml', '10315.METS.xml');

        console.log("----");
        console.log("Now build our own import job from scratch");
        // Note that this is a completely different URI - we can use whatever we like, it's OUR import job
        const importJobId = "https://digirati.com/importjobs/job-" + getShortTimestamp();
        console.log("We can also mint whatever id we like for this job:")
        console.log(`"id": "${importJobId}"`);
        console.log("This time we have to add the sha256 ourselves because we are not asking the server to build the import job");
        // TODO: do we want to require that? As long as there's a METS file in the importJob, the server can use it to look for SHA256 hashes
        const importJob = {
            id: importJobId,
            type: 'ImportJob',
            deposit: newDeposit.id,
            archivalGroup: archivalGroupUri,
            IsUpdate: true,      // TODO: We need to be explicit about this, but should the server work it out?
            containersToAdd: [],
            binariesToAdd: [],
            containersToDelete: [],
            binariesToDelete: [],
            binariesToPatch: [
                {
                    id: archivalGroupUri + '/10315.METS.xml',
                    name: '10315.METS.xml',
                    contentType: 'application/xml',
                    origin: newDeposit.files + '10315.METS.xml',
                    digest: 'c033d56b1c756f718233893ca735a2eb1add86fb4200a99f30c93deb5ffe6adf'    // Likely not require this if METS in payload
                }
            ]
        };
        console.log(importJob);

        const executeJobUri = newDeposit.id + '/importjobs';
        console.log("Now execute the import job...");
        console.log("POST " + executeJobUri);
        console.log("If this fails, check that the sha256 of your local 10315.METS.xml matches the digest above - may be line-ending issue from GitHub");
        const executeImportJobReq = await request.post(executeJobUri, {
            data: importJob
        });
        let importJobResult = await executeImportJobReq.json();
        console.log(importJobResult);
        expect(importJobResult).toEqual(expect.objectContaining({
            type: 'ImportJobResult',
            status: 'waiting',
            archivalGroup: archivalGroupUri
        }));
        console.log("----");

        console.log("... and poll it until it is either complete or completeWithErrors...");
        await waitForStatus(importJobResult.id, /completed.*/, request);
        console.log("----");

        // ### API INTERACTION ###
        console.log("Now request the archival group URI we made earlier:");
        console.log("GET " + archivalGroupUri);
        const archivalGroupReq = await request.get(archivalGroupUri);

        expect(archivalGroupReq.ok()).toBeTruthy();
        const archivalGroup = await archivalGroupReq.json();
        console.log("We expect to see two versions available in this object")
        console.log(archivalGroup);

        expect(archivalGroup).toEqual(expect.objectContaining({
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
                ])
        }));
        console.log("----");


        console.log("Now what if we want to add a fifth JPEG - this is the same as the exporting example, but _without the export_");
        console.log("We need to create a new deposit now that the first deposit has been used to create a new version.");
        const anotherDepositResp = await request.post('/deposits', {
            data: {
                archivalGroup: archivalGroupUri,
                submissionText: "Creating another deposit to add further files"
            }
        })
        const anotherDeposit = await anotherDepositResp.json();
        console.log("We are going to add the same extra image as in the exporting example.")
        const sourceDir = 'samples/10315s-add-jpg/';
        const files = [
            '10315.METS.xml',
            'objects/IbqX6-fA.jpg'
        ];
        for (const file of files) {
            await uploadFile(s3Client, anotherDeposit.files, sourceDir + file, file)
        }
        console.log("And again, generate the import job ourselves, rather than via a diff by the server.")
        console.log("This gives us complete control and allows lightweight updates");
        const importJobId2 = "https://digirati.com/importjobs/job-" + getShortTimestamp();
        const importJob2 = {
            id: importJobId2,
            type: 'ImportJob',
            deposit: anotherDeposit.id,
            archivalGroup: archivalGroupUri,
            IsUpdate: true,      // TODO: We need to be explicit about this, but should the server work it out?
            containersToAdd: [],
            binariesToAdd: [
                {
                    id: archivalGroupUri + '/objects/IbqX6-fA.jpg',
                    name: 'IbqX6-fA.jpg',
                    contentType: 'image/jpeg',
                    origin: anotherDeposit.files + 'objects/IbqX6-fA.jpg',
                    // Leave this off to show that it will be read from the METS
                    digest: '5d235e69c795ec73fd45ed5eb9f75be7f0075abccd4ee0b622bfc3c898379710'
                }
            ],
            containersToDelete: [],
            binariesToDelete: [],
            binariesToPatch: [
                {
                    id: archivalGroupUri + '/10315.METS.xml',
                    name: '10315.METS.xml',
                    contentType: 'application/xml',
                    origin: anotherDeposit.files + '10315.METS.xml',
                    // Leave this off to show that the server will compute it for updated METS
                    // BUT you can still supply it for extra safety.
                    digest: 'b9f622c1cf1a4af8f7c353d2afca0e0f89f26b679e2de8a29450479663025bd8'    // Likely not require this if METS in payload
                }
            ]
        };
        console.log(importJob2);
        console.log("-----");

        console.log("Now execute the SECOND import job...");
        const executeJobUri2 = anotherDeposit.id + '/importjobs';
        console.log("POST " + executeJobUri2);
        const executeImportJobReq2 = await request.post(executeJobUri2, {
            data: importJob2
        });
        let importJobResult2 = await executeImportJobReq2.json();
        console.log(importJobResult2);
        expect(importJobResult2).toEqual(expect.objectContaining({
            type: 'ImportJobResult',
            status: 'waiting',
            archivalGroup: archivalGroupUri
        }));
        console.log("----");

        console.log("... and poll it until it is either complete or completeWithErrors...");
        await waitForStatus(importJobResult2.id, /completed.*/, request);
        console.log("----");

        console.log("Now request the digital object yet again:");
        console.log("GET " + archivalGroupUri);
        const archivalGroupReq3 = await request.get(archivalGroupUri);

        expect(archivalGroupReq3.ok()).toBeTruthy();
        const archivalGroupV3 = await archivalGroupReq3.json();
        console.log("We expect to see THREE versions available in this object")
        console.log(archivalGroupV3);

        expect(archivalGroupV3).toEqual(expect.objectContaining({
            id: archivalGroupUri,
            type: 'ArchivalGroup',
            name: '[Example title]', // This will have been read from the METS file  <mods:title>
            version: expect.objectContaining({ocflVersion: 'v3'}),  // and we expect it to be at version 2
            versions: expect.arrayContaining(
                [
                    expect.objectContaining({ocflVersion:'v1'}),
                    expect.objectContaining({ocflVersion:'v2'}),
                    expect.objectContaining({ocflVersion:'v3'})
                ]
            )
        }));
        console.log("----");
    })
});


// maybe you have these files handy already
// replace jpeg 2 with another binary, same name
// sha256 changes in METS but that's all
// => v2

// then another job - add a fifth JPEG
// => v3