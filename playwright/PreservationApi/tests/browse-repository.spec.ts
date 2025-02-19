import {test, expect} from '@playwright/test';

test('view-repository-root', async ({request}) => {
   const rootReq = await request.get('/repository');
   expect(rootReq.ok()).toBeTruthy();

   const root = await rootReq.json();
   expect(root).toEqual(expect.objectContaining({
       "id": expect.stringContaining('/repository/'),
       type: expect.stringMatching('RepositoryRoot')
   }));
});


test.describe('Traverse repository', () => {
    test('traverse-repository', async ({request}) => {
        const rootReq = await request.get('/repository');
        const root = await rootReq.json();

        expect(root).toEqual(expect.objectContaining({
            containers: expect.arrayContaining([])
        }));

        const foundBinaryId = await walkToBinary(request, root);
        const binaryReq = await request.get(foundBinaryId);
        const binary = await binaryReq.json();
        expect(binary).toEqual(expect.objectContaining({
            type: expect.stringMatching('Binary'),
            digest: expect.any(String),
            partOf: expect.stringContaining('/repository/')
        }));
    });
});

// Walk the repository until you find a Binary
async function walkToBinary(request, parent)
{
    let foundBinaryId = null;
    if(parent.hasOwnProperty("binaries") && parent.binaries.length > 0)
    {
        foundBinaryId = parent.binaries[0]['id'];
    }
    else if(parent.hasOwnProperty("containers") && parent.containers.length > 0)
    {
        for (const c of parent.containers) {
            const ccReq = await request.get(c["id"])
            const cc = await ccReq.json();
            foundBinaryId = await walkToBinary(request, cc);
            if(foundBinaryId) break;
        }
    }
    return foundBinaryId;
}