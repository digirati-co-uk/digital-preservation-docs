import {APIRequestContext, expect} from '@playwright/test';
import {ListObjectsV2Command, paginateListObjectsV2, PutObjectCommand, S3Client} from "@aws-sdk/client-s3";
import {fromIni} from '@aws-sdk/credential-providers';
import {parseS3Url} from 'amazon-s3-url'
import {readFileSync} from "fs";


export function getS3Client() {
    return new S3Client({
        region: "eu-west-1",
        credentials: fromIni({profile: 'leeds'})
    });
}

// This isn't using any of the custom Leeds API at all.
// All file transfer is done using AWS APIs, into S3 buckets.
// You don't even need to set the SHA256 checksum on the uploaded file,
// if that checksum is provided in a METS file, allowing multiple
// ways to get the content into S3
export async function uploadFile(
    s3: S3Client,
    depositUri: string,
    localFilePath: string,
    relativePathInDigitalObject: string) {

    const s3Url = parseS3Url(depositUri);

    // be forgiving of joining paths...
    const key = s3Url.key.endsWith('/') ? s3Url.key.slice(0,-1) : s3Url.key;
    const path = relativePathInDigitalObject.startsWith('/') ? relativePathInDigitalObject.slice(1) : relativePathInDigitalObject;
    const pathInDeposit = key + '/' + path;

    const putCmd = new PutObjectCommand({
        Bucket: s3Url.bucket,
        Key: pathInDeposit,
        Body: readFileSync(localFilePath),
        CacheControl: "no-cache"
        // Note that we don't need to set this if the METS file provides it:
        // ChecksumAlgorithm: "SHA256"
        // But if you DO provide this information in S3 metadata, we will validate it against the METS file.
    });

    console.log("Uploading to S3: " + pathInDeposit);
    await s3.send(putCmd);
}

export async function listKeys(s3: S3Client, parentKey: string){

    const s3Url = parseS3Url(parentKey);
    var opts = {
        Bucket: s3Url.bucket,
        Prefix: parentKey
    }

    const files = [];
    for await (const data of paginateListObjectsV2({ client: s3 }, opts)) {
        files.push(...(data.Contents ?? []));
    }
    for(const f of files){
        console.log(f);
    }
    return files;
}

// This is purely for demo purposes and would be no part of a real application!!
// Its purpose is to produce a short string with very small likelihood of collisions.
export function getShortTimestamp(){
    const date = new Date();
    const dayOfYear = (Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - Date.UTC(date.getFullYear(), 0, 0)) / 24 / 60 / 60 / 1000;
    const secondOfDay = date.getHours() * 3600 + date.getMinutes() * 60 + date.getSeconds();
    return `-${String(dayOfYear).padStart(3, '0')}-${String(secondOfDay).padStart(5, '0')}`
}

export function getSecondOfDay(){
    const date = new Date();
    const secondOfDay = date.getHours() * 3600 + date.getMinutes() * 60 + date.getSeconds();
    return String(secondOfDay).padStart(5, '0');
}

export function getYMD(){
    const date = new Date();
    return date.toISOString().split('T')[0]
}

export async function ensurePath(path: string, request: APIRequestContext) {
    const parts = path.split('/');
    let buildPath = "/repository";
    for (const part of parts) {
        if(part){
            buildPath += '/' + part;
            const resourceResp = await request.get(buildPath);
            if(resourceResp.status() == 404){
                // This is always a container, you can't create other kinds of resource outside of a deposit
                const containerResp = await request.put(buildPath);
            }
            // ignore other status codes for now
        }
    }
}

export async function waitForStatus(uri: string, status: any, request: APIRequestContext){
      await expect.poll(async () => {
        console.log(`polling object: ${uri}`);
        const resp = await request.get(uri);
        const respObj = await resp.json();
        console.log("status: " + respObj.status);
        return respObj.status;
    }, {
        intervals: [2000], // every 2 seconds
        timeout: 60000 // allow 1 minute to complete
    }).toMatch(status);
}