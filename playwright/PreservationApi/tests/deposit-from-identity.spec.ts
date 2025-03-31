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
// Creating a deposit for a new or existing Archival Group, given the Catalogue IRN or ID Service PID
test.describe('Create a NATIVE (our own METS) deposit and put some files in it', () => {

    let newDeposit = null;

    test('create-deposit-from-id', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);


        console.log("POST /deposits/from-identifier");
        const depositReq = await request.post('/deposits/from-identifier', {
            data: {
                "schema": "catirn",   // you can also use "id" or "pid" with the pid value
                "value": "4"   // This is PID yybfgksl
            }
        });

        expect(depositReq.status()).toBe(201);
        newDeposit = await depositReq.json();
        // https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#deposit
        console.log("New Deposit created:");
        console.log(newDeposit);
        console.log("----");

        expect(newDeposit.files).toMatch(/s3:\/\/.*/);
        expect(newDeposit.archivalGroupName).toBe("Spring Lambs")
        expect(newDeposit.archivalGroup).toContain("/cc-test/yybfgksl")
        //                                          /cc/yybfgksl -- in real version

        const sourceDir = 'samples/10315s/';
        const files = [
            '10315.METS.xml',
            'objects/372705s_001.jpg',
            'objects/372705s_002.jpg',
            'objects/372705s_003.jpg',
            'objects/372705s_004.jpg'
        ];
        const s3Client = getS3Client();
        console.log("Uploading " + files.length + " files to the S3 location provided by the Deposit:");
        console.log(newDeposit.files);
        for (const file of files) {
            await uploadFile(s3Client, newDeposit.files, sourceDir + file, file, false) // No need to set checksums - we're providing a METS file
        }
        console.log("----");

        // Now we have uploaded our files.

        console.log("Execute the diff in one operation, without fetching it first (see RFC)")
        // This is a shortcut, a variation on the mechanism shown in create-deposit.spec.ts
        const executeImportJobReq = await request.post(newDeposit.id + '/importjobs', {
            data: { "id": newDeposit.id + '/importjobs/diff' }
        });
        let importJobResult = await executeImportJobReq.json();
        await waitForStatus(importJobResult.id, /completed.*/, request);
        console.log("... and poll it until it is either complete or completeWithErrors...");

        // Creation completed - what follows checks that it did what we expected.


        // Now we should have a preserved digital object in the repository:

        // ### API INTERACTION ###
        console.log("Now request the digital object URI we made earlier:");
        console.log("GET " + newDeposit.archivalGroup);
        const digitalObjectReq = await request.get(newDeposit.archivalGroup);

        expect(digitalObjectReq.ok()).toBeTruthy();
        const digitalObject = await digitalObjectReq.json();
        console.log(digitalObject);
        expect(digitalObject).toEqual(expect.objectContaining({
            'id': newDeposit.archivalGroup,
            type: 'ArchivalGroup',
            name: 'Spring Lambs',
            version: expect.objectContaining({ocflVersion: 'v1'}),  // and we expect it to be at version 1
            binaries: expect.arrayContaining(
                [
                    // and it has a METS file in the root
                    expect.objectContaining({'id': expect.stringContaining('10315.METS.xml')})
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





