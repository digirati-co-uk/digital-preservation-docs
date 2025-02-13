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
// A completely new digital object / package / book / etc.
// Someone has started working on it in Goobi, but it hasn't ever been saved to Preservation.
// Now it's time to commit it to Preservation.
// (later we'll make further changes to it).

// A Deposit is the mechanism to get files in and out of Preservation:
// https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#deposit
test.describe('Create a deposit and put some files in it', () => {

    let newDeposit = null;

    test('create-deposit', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);

        // Before we start, we want to make sure we have a "folder" in the Digital Preservation Repository to
        // save Digital Objects in. You might want to save 1000s of digital objects under the same
        // parent location - but that location needs to exist! Goobi isn't the only user of the repository.
        // And also, Goobi can create child structure.
        // This will be a no-op except the very first time, commenting out for now
        const parentContainer = `/goobi-tests/basic-1/${getYMD()}`;
        await ensurePath(parentContainer, request);

        // We want to have a new WORKING SPACE - a _Deposit_
        // So we ask for one:

        // ### API INTERACTION ###
        console.log("Create a new Deposit:");
        console.log("POST /deposits");
        const depositReq = await request.post('/deposits', {
            data: {}
        }); // expect fail need data {}

        expect(depositReq.status()).toBe(201);
        newDeposit = await depositReq.json();
        // https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#deposit
        console.log("New Deposit created:");
        console.log(newDeposit);
        console.log("----");

        // this deposit could be used for creating a new DigitalObject in
        // the repository, or for updating an existing one.
        // Here we're eventually going to use it to create a new DigitalObject.
        // And if we already know the URI in Preservation that we want that digital object to live at,
        // we can supply it in the initial POST. But we don't have to.
        // (see a later variant where we do supply the `digitalObject` initially)

        // The `files` property of the created deposit gives us an S3 URI
        // from which we can obtain a bucket name and key prefix.
        // It is assumed that, as a known API user, the returned S3 location
        // will be one we can already read and write to.
        // For example, when Goobi asks for a Deposit, the system will
        // return a key within a dedicated bucket set up for Goobi's use in advance.
        // Goobi will already have credentials to interact with this bucket.
        expect(newDeposit.files).toMatch(/s3:\/\/.*/);

        // Now we'll upload the files for a very simple object.
        // We can spend as long as we like here - seconds, as below.
        // Or we can leave this "open" for days, updating files as we like, in multiple
        // separate operations.
        // ******************************
        // At no point in uploading files are we interacting with the Preservation API.
        // Only pure AWS S3 APIs.
        // ******************************
        // For simplicity, we're going to use the same relative paths in the Deposit as we have locally on disk.
        // We don't HAVE to do this, they can take any layout in the bucket, as long as:
        //  - they are all paths that *start with* deposit.files (an s3 URI)
        //  - the paths conform to the reduced character set (likely a-zA-Z0-9, and -._)
        // The second point is not enforced here because this is
        // using whatever AWS S3 library you like. It is enforced later.
        const sourceDir = 'samples/10315s/';
        const files = [
            '10315.METS.xml',             // we don't need to tell the API that this is the METS file, it will find it
            'objects/372705s_001.jpg',
            'objects/372705s_002.jpg',
            'objects/372705s_003.jpg',
            'objects/372705s_004.jpg'
        ];
        const s3Client = getS3Client();
        console.log("Uploading " + files.length + " files to the S3 location provided by the Deposit:");
        console.log(newDeposit.files);
        for (const file of files) {
            await uploadFile(s3Client, newDeposit.files, sourceDir + file, file)
        }
        console.log("----");

        // Now we have uploaded our files. The next step is to create in ImportJob
        // https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#importjob
        // We could do this manually, for the files we have just placed in the Deposit.
        // A simpler method for this initial save to preservation is to ask the API to generate
        // an ImportJob for us, from the difference between the digital object in Preservation,
        // and the file in the Deposit.

        // However, we need to provide one additional piece of information:
        // the URI (location) of the digital object in the repository - where we are going to save it
        // To allow the same object to be created multiple times without having to
        // clear out the repository, I'm going to append a timestamp to this URI.
        // WE WOULD NOT DO THAT IN A REAL SCENARIO!
        let preservedDigitalObjectUri = `${baseURL}/repository${parentContainer}/ms-10315-${getSecondOfDay()}`;

        // ### API INTERACTION ###
        console.log("Adding our intended DigitalObject (package, preserved digital object) URI to the deposit with a PATCH");
        console.log("The URI of the preserved digital object will be:")
        console.log(preservedDigitalObjectUri);
        const depositWithDestination = await request.patch(newDeposit.id, {
            data: {
                archivalGroup: preservedDigitalObjectUri,
                submissionText: "You can write what you like here"
            }
        });
        console.log("----");


        expect(await depositWithDestination.json()).toEqual(expect.objectContaining({
            "id": newDeposit.id,  // verify that it's the same deposit!
            archivalGroup: preservedDigitalObjectUri
        }));
        // We could have provided this information in the initial POST to create the deposit.
        // I suspect Goobi will know at the start where this should live in Preservation.
        // But some other scenarios might not know that during the initial assembly of files stage.

        // Now we can get the API to generate an ImportJob for us:
        const diffJobGeneratorUri = newDeposit.id + '/importjobs/diff';


        // ### API INTERACTION ###
        console.log("Asking service to generate an import job from the deposit files (a diff)...");
        console.log("GET " + diffJobGeneratorUri);
        const diffReq = await request.get(diffJobGeneratorUri);

        const diffImportJob = await diffReq.json();
        console.log(diffImportJob);
        console.log("----");

        // You could edit diffImportJob here, e.g., to remove some files, change names.
        // Notice that the server has used information in the METS as well as the S3 layout.
        //  - It has extracted checksums from the METS
        //  - It has extracted the "real" file names from METS
        //  - It has extracted the name of the Archival Group from the METS (mods:title)
        //  - (it would also extract real Container names too)

        // We will just execute the job as-is, by POSTing it:

        // ### API INTERACTION ###
        const executeJobUri = newDeposit.id + '/importjobs';
        console.log("Now execute the import job...");
        console.log("POST " + executeJobUri);
        const executeImportJobReq = await request.post(executeJobUri, {
            data: diffImportJob
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
        // There is a way of executing a diff import job in one step, without having to see the body
        // - see https://github.com/uol-dlip/docs/blob/main/rfcs/003-preservation-api.md#execute-import-job
        // but the above allows us to see what we are about to ask for.
        // It also allows us to override the name or other aspects.

        // We could now go away and do something else, as this job might in a long queue.
        // For this test we'll just wait for it to complete - which means that the status is
        // either "completed" or "completedWithErrors",

        console.log("... and poll it until it is either complete or completeWithErrors...");
        await waitForStatus(importJobResult.id, /completed.*/, request);
        console.log("----");

        // Now we should have a preserved digital object in the repository:

        // ### API INTERACTION ###
        console.log("Now request the digital object URI we made earlier:");
        console.log("GET " + preservedDigitalObjectUri);
        const digitalObjectReq = await request.get(preservedDigitalObjectUri);

        expect(digitalObjectReq.ok()).toBeTruthy();
        const digitalObject = await digitalObjectReq.json();
        console.log(digitalObject);
        expect(digitalObject).toEqual(expect.objectContaining({
            'id': preservedDigitalObjectUri,
            type: 'ArchivalGroup',
            name: '[Example title]', // This will have been read from the METS file  <mods:title>
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








