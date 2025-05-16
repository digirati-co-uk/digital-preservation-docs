import {APIRequestContext, expect, test} from "@playwright/test";
import {createArchivalGroup, createDeposit} from "./quick-prep.spec";
import {getAuthHeaders} from "./common-utils";

async function logDepositLockDetails(request: APIRequestContext, deposit, headers) {
    const depositResp = await request.get(deposit.id, { headers: headers });
    expect(depositResp.status()).toBe(200);
    const returnedDeposit = await depositResp.json();
    console.log("Deposit locked by " + returnedDeposit.lockedBy);
    console.log("Deposit locked date " + returnedDeposit.lockDate);
    return returnedDeposit;
}

test.describe('Locking and unlocking a deposit', () => {


    test('locking-and-unlocking', async ({request, baseURL}) => {

        // Set a very long timeout so you can debug on breakpoints or whatnot.
        test.setTimeout(1000000);
        const headers = await getAuthHeaders(baseURL);

        // Background prep
        console.log("Starting condition is a Preserved Digital Object in the repository - we'll make one for this test");
        const deposit = await createDeposit(request, baseURL, headers);
        console.log("Created deposit " + deposit.id);

        // The demonstration
        // This test is a halfway house at present; you need to set a breakpoint and then try things as a different user.
        // This means both using the UI, and the API with a different client secret.

        // Try doing some stuff in the UI now
        // It should be fine, the deposit is not locked

        const lockUri = deposit.id + '/lock';
        console.log("Locking deposit " + lockUri);
        const lockResp = await request.post(lockUri, {
            headers: headers
        });
        expect(lockResp.status()).toBe(204);

        // get the deposit again
        const lockedDeposit = await logDepositLockDetails(request, deposit, headers);

        // Now try some more stuff in the UI
        // Should be prevented from changes

        // Now unlock it
        console.log("Unlocking deposit " + lockUri);
        const deleteLockResp = await request.delete(lockUri, {
            headers: headers
        });
        expect(deleteLockResp.status()).toBe(204);

        // now do some more stuff in the UI and succeed

        // Now lock the deposit as a different user, e.g., in the UI

        // get the deposit again
        const lockedDeposit2 = await logDepositLockDetails(request, deposit, headers);

        // We'll try to add a file to METS (doesn't matter that we didn't upload it, it should be rejected)
        const metsUri = deposit.id + '/mets';
        const metsResp = await request.get(metsUri, { headers: headers });
        expect(metsResp.status()).toBe(200);
        const eTag = metsResp.headers()["etag"];
        console.log("posting to METS file:");

        const ifMatchHeaders = structuredClone(headers);
        ifMatchHeaders["If-Match"] = eTag;
        let metsUpdateResp = await request.post(metsUri, {
            data: [ "objects/some-new-file.tiff" ],
            headers: ifMatchHeaders
        });
        // Leave soft for now as I can't have another user on localhost atm
        expect.soft(metsUpdateResp.status()).toBe(409);

        // try to get our own lock

        console.log("Locking deposit again " + lockUri);
        const lockResp2 = await request.post(lockUri, {
            headers: headers
        });
        expect.soft(lockResp2.status()).toBe(409); // because still locked by another

        // we need to force it

        const forceLockUri = deposit.id + '/lock?force=true';
        console.log("Locking deposit again, with force " + lockUri);
        const forceLockResp = await request.post(forceLockUri, {
            headers: headers
        });
        expect(forceLockResp.status()).toBe(204); // now OK

        // Now try editing again - it won't be a conflict
        // (won't work, but we're just testing the conflict)

        console.log("posting to METS file again:");
        const ifMatchHeaders2 = structuredClone(headers);
        ifMatchHeaders2["eTag"] = eTag;
        metsUpdateResp = await request.post(metsUri, {
            data: [ "objects/some-new-file.tiff" ],
            headers: ifMatchHeaders2
        });
        expect(metsUpdateResp.status()).toBe(400); // a different error because we can't edit this non-native METS like this

        // Now in the UI try removing the lock through the actions menu
        // (in the ui)

        const unlockedDeposit = await logDepositLockDetails(request, deposit, headers);
        expect(unlockedDeposit.lockedBy).toBeNull();




    })
});