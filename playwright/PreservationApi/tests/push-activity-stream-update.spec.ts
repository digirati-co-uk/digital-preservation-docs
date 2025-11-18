import {expect, test} from '@playwright/test';
import {getAuthHeaders} from "./common-utils";

test.describe('Force an activity onto the Activity Stream', () => {

    test('push-activity', async ({request, baseURL}) => {

        test.setTimeout(1000000);

        const existingArchivalGroup = baseURL + "/repository/native-tests/basic-1/2025-05-07/ms-10315-58391";
        const headers = await getAuthHeaders(baseURL);

        const activity = {
            "type": "Update",
            "object": {
                "id": existingArchivalGroup,
                "type": "ArchivalGroup"
            }
        };

        const pushResponse = await request.post('/activity/archivalgroups/collection', {
            data: activity,
            headers: headers
        });

        expect(pushResponse.status()).toBe(204);

        const collResponse =  await request.get('/activity/archivalgroups/collection', {
            headers: headers
        });
        expect(collResponse.status()).toBe(200);
        const collection = await collResponse.json();

        const pageResponse =  await request.get(collection.last.id, {
            headers: headers
        });
        expect(pageResponse.status()).toBe(200);
        const page = await pageResponse.json();

        const lastActivity = page.orderedItems.pop();

        expect(lastActivity).toEqual(expect.objectContaining({
            type: "Update",
            object: expect.objectContaining({
                id: existingArchivalGroup,
                type: "ArchivalGroup"
            }),
            endTime: expect.stringContaining("" + new Date().getFullYear())
        }))



        // TODO - all the error conditions.

    })
});