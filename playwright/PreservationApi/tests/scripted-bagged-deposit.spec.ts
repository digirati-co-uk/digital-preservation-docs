import {expect, test} from '@playwright/test';
import {
    getS3Client,
    uploadFile,
    ensurePath,
    waitForStatus,
    getYMD,
    getSecondOfDay
} from './common-utils'


test.describe('Create a NATIVE (our own METS) deposit in BagIt layout, and put files in it that have been analysed by tools in a BitCurator environment.', () => {

    let newDeposit = null;

    test('create-deposit', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);

        const parentContainer = `/native-tests/bagged/${getYMD()}`;
        await ensurePath(parentContainer, request);

        // We want to have a new WORKING SPACE - a _Deposit_
        // So we ask for one:

        // ### API INTERACTION ###

        const secondOfDay = getSecondOfDay();
        let preservedDigitalObjectUri = `${baseURL}/repository${parentContainer}/bc-example-1-${secondOfDay}`;
        const agName = "Bagged layout test " + secondOfDay;
        console.log("Create a new Deposit:");
        console.log("POST /deposits");
        const depositReq = await request.post('/deposits', {
            data: {
                type: "Deposit",
                templateType: "BagIt", // the layout
                archivalGroup: preservedDigitalObjectUri,
                archivalGroupName: agName,
                submissionText: "This should create a data directory, with objects/, metadata/ and mets.xml within it."
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
        const sourceDir = 'samples/bc-example-1/';

        // on Windows, if you are in the bc-example-1 folder, this will give you the output below:
        // (gci -Recurse *.*|Resolve-Path -Relative) -replace "\.\\","" -replace "\\","/" | Foreach-Object { '"' + $_  + '",'}
        // BEWARE this is a bit naive, what about quotes as part of filenames?
        const files = [
            "data/metadata/brunnhilde/csv_reports/formats.csv",
            "data/metadata/brunnhilde/csv_reports/formatVersions.csv",
            "data/metadata/brunnhilde/csv_reports/mimetypes.csv",
            "data/metadata/brunnhilde/csv_reports/years.csv",
            "data/metadata/brunnhilde/logs/viruscheck-log.txt",
            "data/metadata/brunnhilde/report.html",
            "data/metadata/brunnhilde/siegfried.csv",
            "data/metadata/brunnhilde/tree.txt",
            "data/metadata/siegfried/siegfied.yml",
            "data/objects/awkward/7 ways to celebrate #WomensHistoryMonth 💜 And a sneak peek at SICK new art.htm",
            "data/objects/awkward/慷獹琠散敬牢瑡圣浯湥䡳獩潴祲潍瑮㼿䄠摮愠猠敮歡瀠敥瑡匠䍉敮⁷牡�.msg",
            "data/objects/nyc/DSCF0969.JPG",
            "data/objects/nyc/DSCF0981.JPG",
            "data/objects/nyc/DSCF0993.JPG",
            "data/objects/nyc/DSCF1004.JPG",
            "data/objects/nyc/DSCF1008.JPG",
            "data/objects/nyc/DSCF1044.JPG",
            "data/objects/nyc/DSCF1090.JPG",
            "data/objects/nyc/DSCF1128.JPG",
            "data/objects/nyc/DSCF1156.JPG",
            "data/objects/Fedora-Usage-Principles.docx",
            "data/objects/IMAGE-2.tiff",
            "data/objects/warteck.jpg",
            "bag-info.txt",
            "bagit.txt",
            "manifest-sha256.txt",
            "tagmanifest-sha256.txt"
        ];
        const s3Client = getS3Client();
        console.log("Uploading " + files.length + " files to the S3 location provided by the Deposit:");
        console.log(newDeposit.files);
        for (const file of files) {
            await uploadFile(s3Client, newDeposit.files, sourceDir + file, file, false) // DO NOT CHECKSUM - see if we can lean on the extra metadata
        }
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
        const fileSystemUri = newDeposit.id + '/filesystem?refresh=true';
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
        const objects = fileSystem.directories.find(d => d.localPath == 'data/objects');
        expect(objects).not.toBeNull();
        expect(objects.files).toHaveLength(3); // the three files in the root of object

        // but these aren't in the METS file; we can call an additional endpoint to add them,
        // using the information in the filesystem (most importantly, the hash or digest)
        console.log("posting to METS file:");

        // We should be able to use files as-is
        // if the files are data/* or root files, ignore
        // we should also be able to send the same list where root files are removed and
        // "data/" is stripped from the files beginning objects/ or /metadata.
        // The ambiguity is files like mets.xml in the "root" - but you're not supposed to add things there!

        // The following call should gather all available metadata sources in the deposit:
        //   - bagit manifest
        //   - siegfried.csv and/or yaml
        //   - and anything else
        // ... and use them as it populates the METS with digests and pronom data.

        // I think it should populate the WorkingDirectory / file system with sha256 and content types too
        // ??? see what happens
        let metsUpdateResp = await request.post(metsUri, {
            data: files, // The list of file paths we defined earlier
            headers: {
                "If-Match": eTag // can't modify METS without this
            }
        });
        expect(metsUpdateResp.status()).toBe(200);
        const itemsAffected = await metsUpdateResp.json();
        expect(itemsAffected.items).toHaveLength(23); // the number of things we added to METS - what about containers!
        console.log("----");
        console.log("items affected:");
        console.log(itemsAffected);

        // now we can try to create an import job
        const diffJobGeneratorUri = newDeposit.id + '/importjobs/diff';
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
                    // We want to be sure that the IDs have become normalised, and the names preserve the original file names.
                    // and an objects folder with 3 files in it
                    expect.objectContaining(
                        {
                            type: 'Container',
                            name: 'objects',
                            binaries: expect.arrayContaining(
                                [
                                    expect.objectContaining({'id': expect.stringContaining('/objects/Fedora-Usage-Principles.docx')}),
                                    expect.objectContaining({'id': expect.stringContaining('/objects/IMAGE-2.tiff')}),
                                    expect.objectContaining({'id': expect.stringContaining('/objects/warteck.jpg')})
                                ]
                            ),
                            containers: expect.arrayContaining(
                                [
                                    expect.objectContaining({'id': expect.stringContaining(('/objects/awkward'))}),
                                    expect.objectContaining(
                                        {
                                            id: expect.stringContaining('/objects/nyc'),
                                            binaries: expect.arrayContaining(
                                                [
                                                    expect.objectContaining({'id': expect.stringContaining('/objects/nyc/DSCF0969.JPG')})
                                                ]
                                            )
                                        }
                                    )
                                ]
                            )
                        }
                    )
                ])
        }));
    });
});








