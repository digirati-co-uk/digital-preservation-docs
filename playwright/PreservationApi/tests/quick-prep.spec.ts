// This does the same thing as the create-deposit example, but without the extra comments

import {APIRequestContext, expect} from "@playwright/test";
import {ensurePath, getS3Client, getShortTimestamp, getYMD, uploadFile, waitForStatus} from "./common-utils";


export async function createDeposit(request: APIRequestContext, baseURL: string, headers){
    const digitalPreservationParent = `/_for_testing/generic-archival-group/${getShortTimestamp()}`;
    await ensurePath(digitalPreservationParent, request, headers);
    const preservedArchivalGroupUri = `${baseURL}/repository${digitalPreservationParent}/ms-10315`;
    const newDepositResp = await request.post('/deposits', {
        data: {
            archivalGroup: preservedArchivalGroupUri,
            submissionText: "Creating a new deposit to demonstrate updates"
        },
        headers: headers
    })
    const newDeposit = await newDepositResp.json();
    const sourceDir = 'samples/10315s/';
    const files = [
        '10315.METS.xml',
        'objects/372705s_001.jpg',
        'objects/372705s_002.jpg',
        'objects/372705s_003.jpg',
        'objects/372705s_004.jpg'
    ];
    const s3Client = getS3Client();
    for (const file of files) {
        await uploadFile(s3Client, newDeposit.files, sourceDir + file, file)
    }
    return newDeposit;
}

export async function createArchivalGroup(request: APIRequestContext, baseURL: string, headers){

    const newDeposit = await createDeposit(request, baseURL, headers);

    console.log("Execute the diff in one operation, without fetching it first (see RFC)")
    // This is a shortcut, a variation on the mechanism shown in create-deposit.spec.ts
    const executeImportJobReq = await request.post(newDeposit.id + '/importjobs', {
        data: { "id": newDeposit.id + '/importjobs/diff' },
        headers: headers,
    });
    let importJobResult = await executeImportJobReq.json();
    await waitForStatus(importJobResult.id, /completed.*/, request, headers);
    return newDeposit.archivalGroup;
}