import {expect, test} from '@playwright/test';
import {
    getS3Client,
    uploadFile,
    ensurePath,
    waitForStatus,
    getYMD,
    getSecondOfDay
} from './common-utils'
import {readFileSync} from "fs";


test.describe('Create Import Jobs for the Storage API directly', () => {

    let newDeposit = null;

    test('storage-import', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);

        const parentContainer = 'import-tests/storage-api-direct/awkward-uris';
        const title = `${getYMD()}-${getSecondOfDay()}`;
        const replacePath = `${parentContainer}/${title}`;

        const template = readFileSync("samples/custom-storage-import/awkward-1-hash-escaped.json", "utf-8");
        let replaced = template
            .replace(/___replace_path___/g, replacePath)
            .replace(/___replace_name___/g, title)
            .replace(/___transient_id___/g, title);
        let importJob = JSON.parse(replaced);

        // ### API INTERACTION ###
        console.log("Now execute the import job...");
        const executeImportJobReq = await request.post("import", {
            data: importJob
        });

        let importJobResult = await executeImportJobReq.json();
        console.log(importJobResult);
        console.log("... and poll it until it is either complete or completeWithErrors...");
        await waitForStatus(importJobResult.id, /completed.*/, request);
        console.log("----");
    });
});








