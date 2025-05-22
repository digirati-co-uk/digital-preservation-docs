import {test, expect} from '@playwright/test';
import {getAuthHeaders} from "./common-utils";

test('view-repository-root', async ({request, baseURL}) => {

    const headers = await getAuthHeaders(baseURL);

    const rootReq = await request.get('/repository', {
        headers: headers
    });
   expect(rootReq.ok()).toBeTruthy();

   const root = await rootReq.json();
   expect(root).toEqual(expect.objectContaining({
       "id": expect.stringContaining('/repository/'),
       type: expect.stringMatching('RepositoryRoot')
   }));
});


test.describe('Traverse repository', () => {

    test('traverse-repository', async ({request, baseURL}) => {

        const headers = await getAuthHeaders(baseURL);
        const rootReq = await request.get('/repository', {
            headers: headers
        });
        const root = await rootReq.json();

        expect(root).toEqual(expect.objectContaining({
            containers: expect.arrayContaining([])
        }));

        const foundBinaryId = await walkToBinary(request, root, headers);
        console.log("Found a binary: " + foundBinaryId);
        const binaryReq = await request.get(foundBinaryId, {
            headers: headers
        });
        const binary = await binaryReq.json();
        expect(binary).toEqual(expect.objectContaining({
            type: expect.stringMatching('Binary'),
            digest: expect.any(String),
            partOf: expect.stringContaining('/repository/')
        }));
    });
});

// Walk the repository until you find a Binary
async function walkToBinary(request, parent, headers)
{
    let foundBinaryId = null;
    if(parent.hasOwnProperty("binaries") && parent.binaries.length > 0)
    {
        foundBinaryId = parent.binaries[0]['id'];
    }
    else if(parent.hasOwnProperty("containers") && parent.containers.length > 0)
    {
        for (const c of parent.containers) {
            const ccReq = await request.get(c["id"], {
                headers: headers
            })
            const cc = await ccReq.json();
            foundBinaryId = await walkToBinary(request, cc, headers);
            if(foundBinaryId) break;
        }
    }
    return foundBinaryId;
}