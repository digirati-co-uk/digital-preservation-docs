import {expect, test} from '@playwright/test';
import {
    getS3Client,
    uploadFile,
    ensurePath,
    waitForStatus,
    getYMD,
    getSecondOfDay
} from './common-utils'

// Scenario:
// A completely new archival group / package / book / etc.
// Someone has started working on it in Goobi, but it hasn't ever been saved to Preservation.
// Now it's time to commit it to Preservation.
// (later we'll make further changes to it).

// A Deposit is the mechanism to get files in and out of Preservation:
// https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#deposit
test.describe('Create a NATIVE (our own METS) deposit and put some files in it', () => {

    let newDeposit = null;

    test('create-deposit', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);

        const parentContainer = `/native-tests/basic-1/${getYMD()}`;
        await ensurePath(parentContainer, request);

        // We want to have a new WORKING SPACE - a _Deposit_
        // So we ask for one:

        // ### API INTERACTION ###

        const secondOfDay = getSecondOfDay();
        let preservedDigitalObjectUri = `${baseURL}/repository${parentContainer}/ms-10315-${secondOfDay}`;
        const agName = "Native test " + secondOfDay;
        console.log("Create a new Deposit:");
        console.log("POST /deposits");
        const depositReq = await request.post('/deposits', {
            data: {
                type: "Deposit",
                useObjectTemplate: true,  // This is what tells the API it's one of ours
                archivalGroup: preservedDigitalObjectUri,
                archivalGroupName: agName,
                submissionText: "This is going to create a METS file and edit the METS as we go"
            }
        });

        expect(depositReq.status()).toBe(201);
        newDeposit = await depositReq.json();
        // https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#deposit
        console.log("New Deposit created:");
        console.log(newDeposit);
        console.log("----");

        expect(newDeposit.files).toMatch(/s3:\/\/.*/);

        // Unlike the create-deposit.spec example, we ARE going to set the checksum, because we have no
        // other way of providing it. Later we will be able to get checksums from BagIt.
        const sourceDir = 'samples/10315s/';
        const files = [
            // NO METS FILE! Compare with create-deposit.spec
            'objects/372705s_001.jpg',
            'objects/372705s_002.jpg',
            'objects/372705s_003.jpg',
            'objects/372705s_004.jpg'
        ];
        const s3Client = getS3Client();
        console.log("Uploading " + files.length + " files to the S3 location provided by the Deposit:");
        console.log(newDeposit.files);
        for (const file of files) {
            await uploadFile(s3Client, newDeposit.files, sourceDir + file, file, true)
        }
        console.log("----");

        // Now we have uploaded our files.
        // But the above S3 helper doesn't know anything, it's just putting some files in a bucket.
        // The Preservation API isn't even aware of what's going on.

        // What happens of we just try to create an import job without doing anything?
        const diffJobGeneratorUri = newDeposit.id + '/importjobs/diff';
        // ### API INTERACTION ###
        console.log("Asking service to generate an import job from the deposit files (a diff)...");
        console.log("GET " + diffJobGeneratorUri);
        const diffResp = await request.get(diffJobGeneratorUri);

        // WE EXPECT HTTP 422 Unprocessable - we haven't described the files in METS!
        expect(diffResp.status()).toBe(422);
        const unprocessableImportJob = await diffResp.json();
        console.log(unprocessableImportJob);
        console.log("----");

        // We could do this by hand - edit the METS file out of sight of the Preservation API.
        // But we can ask the Preservation API to help us.

        // We can do several things here. We can view the METS directly as XML
        // GET /deposits/aabbccdd/mets
        // We can POST a List of relative paths
        // POST /deposits/aabbccdd/mets  ... body is an array of strings, e.g., objects/my-file

        const metsUri = newDeposit.id + '/mets';
        const metsResp = await request.get(metsUri);
        expect(metsResp.status()).toBe(200);
        const eTag = metsResp.headers()["etag"];

        // We can have a look at the filesystem that has resulted from our uploads
        // to the deposit:
        const fileSystemUri = newDeposit.id + '/filesystem';
        let fileSystemResp = await request.get(fileSystemUri);
        expect(fileSystemResp.status()).toBe(200);
        let fileSystem = await fileSystemResp.json();
        console.log("----");
        console.log("filesystem:");
        console.log(fileSystem);
        console.log("----");
        // The above is not used in this test, it's just to demonstrate that you can inspect the filesystem
        // of the deposit via the API. (The UI app does not go via the API for this - it uses the same
        // library but interacts with the filesystem directly)

        // In this example, it's easy to navigate this filesystem:
        const objects = fileSystem.directories[0];
        expect(objects.files).toHaveLength(4); // the four files mentioned above

        // but these aren't in the METS file; we can call an additional endpoint to add them,
        // using the information in the filesystem (most importantly, the hash or digest)
        console.log("posting to METS file:");
        let metsUpdateResp = await request.post(metsUri, {
           data: files, // The list of file paths we defined earlier
           headers: {
               "If-Match": eTag // can't modify METS without this
           }
        });
        expect(metsUpdateResp.status()).toBe(200);
        const itemsAffected = await metsUpdateResp.json();
        expect(itemsAffected.items).toHaveLength(4);
        console.log("----");
        console.log("items affected:");
        console.log(itemsAffected);

        // now we can try to create an import job
        const secondDiffResp = await request.get(diffJobGeneratorUri);
        expect(secondDiffResp.status()).toBe(200);
        const importJob = await secondDiffResp.json();
        console.log("----");
        console.log("Working import job:");
        console.log(importJob);
        console.log("----");

        // ### API INTERACTION ###
        const executeJobUri = newDeposit.id + '/importjobs';
        console.log("Now execute the import job...");
        console.log("POST " + executeJobUri);
        const executeImportJobReq = await request.post(executeJobUri, {
            data: importJob
        });

        let importJobResult = await executeImportJobReq.json();
        console.log(importJobResult);
        expect(importJobResult).toEqual(expect.objectContaining({
            type: 'ImportJobResult',
            originalImportJob: diffJobGeneratorUri, // <++ here
            status: 'waiting',
            archivalGroup: preservedDigitalObjectUri
        }));
        console.log("----");

        console.log("... and poll it until it is either complete or completeWithErrors...");
        await waitForStatus(importJobResult.id, /completed.*/, request);
        console.log("----");

        // Now we should have a preserved archival group in the repository:

        // ### API INTERACTION ###
        console.log("Now request the archival group URI we made earlier:");
        console.log("GET " + preservedDigitalObjectUri);
        const digitalObjectReq = await request.get(preservedDigitalObjectUri);

        expect(digitalObjectReq.ok()).toBeTruthy();
        const digitalObject = await digitalObjectReq.json();
        console.log(digitalObject);
        expect(digitalObject).toEqual(expect.objectContaining({
            id: preservedDigitalObjectUri,
            type: 'ArchivalGroup',
            name: agName, // This will have been read from the METS file  <mods:title>
            version: expect.objectContaining({ocflVersion: 'v1'}),  // and we expect it to be at version 1
            binaries: expect.arrayContaining(
                [
                    // and it has a METS file in the root
                    expect.objectContaining({'id': expect.stringContaining('mets.xml')})
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
                                    expect.objectContaining({'id': expect.stringContaining('/objects/372705s_001.jpg')}),
                                    expect.objectContaining({'id': expect.stringContaining('/objects/372705s_002.jpg')}),
                                    expect.objectContaining({'id': expect.stringContaining('/objects/372705s_003.jpg')}),
                                    expect.objectContaining({'id': expect.stringContaining('/objects/372705s_004.jpg')}),
                                ]
                            )
                        }
                    )
                ])
        }));
    });
});








