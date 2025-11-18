import {expect, test} from '@playwright/test';
import {getAuthHeaders} from "./common-utils";

test.describe('Read Activity Stream', () => {

    test('read-activity', async ({request, baseURL}) => {

        test.setTimeout(1000000);

        const headers = await getAuthHeaders(baseURL);

        const collResponse =  await request.get('/activity/archivalgroups/collection', {
            headers: headers
        });
        expect(collResponse.status()).toBe(200);
        const collection = await collResponse.json();

        let prevPageLink = collection.last.id;
        let lastActivityDate: Date = new Date();
        while(prevPageLink) {
            console.log();
            console.log("Getting a new page");
            console.log("prevPageLink = " + prevPageLink);
            const pageResponse =  await request.get(prevPageLink, {
                headers: headers
            });
            expect(pageResponse.status()).toBe(200);
            const page = await pageResponse.json();
            let activity = page.orderedItems.pop();
            while(activity) {
                console.log("lastActivity.endTime = " + activity.endTime);
                const thisActivityDate = new Date(activity.endTime);
                expect(thisActivityDate < lastActivityDate).toBeTruthy();
                lastActivityDate = thisActivityDate;
                activity = page.orderedItems.pop();
            }

            prevPageLink = null;
            if(page.prev){
                prevPageLink = page.prev.id;
            }
        }





        // TODO - all the error conditions.

    })
});