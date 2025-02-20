export function getBoilerPlateManifest() {
    // This is not necessarily what the production IIIF-Builder would do
    // Probably load a template from a file.

    // This is the stuff that every published Manifest will have.
    // The real template will probably have more.
    return {
        "type": "Manifest",
        "provider": [
            {
                "id": "https://example.org/about",
                "type": "Agent",
                "label": {"en": ["Example Organization"]},
                "homepage": [
                    {
                        "id": "https://example.org/",
                        "type": "Text",
                        "label": {"en": ["Example Organization Homepage"]},
                        "format": "text/html"
                    }
                ],
                "logo": [
                    {
                        "id": "https://example.org/images/logo.png",
                        "type": "Image",
                        "format": "image/png",
                        "height": 100,
                        "width": 120
                    }
                ],
                "seeAlso": [
                    {
                        "id": "https://data.example.org/about/us.jsonld",
                        "type": "Dataset",
                        "format": "application/ld+json",
                        "profile": "https://schema.org/"
                    }
                ]
            }
        ]
    }
}

export class IdentityServiceClient {
    async getIdentifier(uri: string, type: IdentifierTypes) {
        switch (type) {
            case IdentifierTypes.IIIFManifest:
                return "https://iiif.leeds.ac.uk/eprints/a6gr99n3";
                break;
        }
        return ""; // obvs not sensible...
    }

    async getIdentifiers(uri: string) {
        return {
            IdentifierTypes.IIIFManifest: "https://iiif.leeds.ac.uk/eprints/a6gr99n3",
            IdentifierTypes.CatalogueApi: "https://catalogue.leeds.ac.uk/a6gr99n3"

        }
    }
}

export class CatalogueApiClient {
    async getRecord(uri: string) {
        return {
            id: uri,
            title: "An EPrints book",
            author: "E. P. Rinse"
        }
    }
}


export enum IdentifierTypes {
    ArchivalGroup,
    IIIFManifest,
    EMuIRN,
    CatalogueApi
}


// eslint-disable-next-line @typescript-eslint/no-unused-vars
const sampleArchivalGroup =
    {
        "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie",
        "type": "ArchivalGroup",
        "version": {
            "mementoTimestamp": "20250128110543",
            "mementoDateTime": "2025-01-28T11:05:43",
            "ocflVersion": "v3"
        },
        "name": "talking to Jodie",
        "versions": [{
            "mementoTimestamp": "20250127114735",
            "mementoDateTime": "2025-01-27T11:47:35",
            "ocflVersion": "v1"
        }, {
            "mementoTimestamp": "20250127115013",
            "mementoDateTime": "2025-01-27T11:50:13",
            "ocflVersion": "v2"
        }, {"mementoTimestamp": "20250128110543", "mementoDateTime": "2025-01-28T11:05:43", "ocflVersion": "v3"}],
        "storageMap": {
            "version": {
                "mementoTimestamp": "20250128110543",
                "mementoDateTime": "2025-01-28T11:05:43.435376Z",
                "ocflVersion": "v3"
            },
            "storageType": "S3",
            "root": "dlip-pres-dev-fedora",
            "objectPath": "initial/eb4/b73/204/eb4b73204253a2a919e5dea4c08fac287956e388fc5459323cef6f953ac40293",
            "files": {
                "mets.xml": {
                    "hash": "1a2b0bcd368f98015530670eed7978233be747ef7a25934e4eab4f05d55bd831",
                    "fullPath": "v3/content/mets.xml"
                },
                "objects/folder-b/folder-bb/minutes-laqm-22-april-2020.pdf": {
                    "hash": "310fa7a479e0d0f79caf21e6a2c607e81bb0ccd5c2829bff7b816a49925419e7",
                    "fullPath": "v1/content/objects/folder-b/folder-bb/minutes-laqm-22-april-2020.pdf"
                },
                "objects/minutes-laqm-8-sept-2020.pdf": {
                    "hash": "9c5aa04a39812c80bcc824e366044c16fb090efb076c8552ca9ca932f0dfc981",
                    "fullPath": "v1/content/objects/minutes-laqm-8-sept-2020.pdf"
                },
                "objects/minutes-laqm-21-june-2020.pdf": {
                    "hash": "eb634d64ce8e6be5195174ceaef9ac9e19c37119f3b31618630aa633ccdbf68f",
                    "fullPath": "v1/content/objects/minutes-laqm-21-june-2020.pdf"
                }
            },
            "hashes": {
                "1a2b0bcd368f98015530670eed7978233be747ef7a25934e4eab4f05d55bd831": "v3/content/mets.xml",
                "310fa7a479e0d0f79caf21e6a2c607e81bb0ccd5c2829bff7b816a49925419e7": "v1/content/objects/folder-b/folder-bb/minutes-laqm-22-april-2020.pdf",
                "9c5aa04a39812c80bcc824e366044c16fb090efb076c8552ca9ca932f0dfc981": "v1/content/objects/minutes-laqm-8-sept-2020.pdf",
                "eb634d64ce8e6be5195174ceaef9ac9e19c37119f3b31618630aa633ccdbf68f": "v1/content/objects/minutes-laqm-21-june-2020.pdf"
            },
            "headVersion": {
                "mementoTimestamp": "20250128110543",
                "mementoDateTime": "2025-01-28T11:05:43.435376Z",
                "ocflVersion": "v3"
            },
            "allVersions": [{
                "mementoTimestamp": "20250127114735",
                "mementoDateTime": "2025-01-27T11:47:35.803193Z",
                "ocflVersion": "v1"
            }, {
                "mementoTimestamp": "20250127115013",
                "mementoDateTime": "2025-01-27T11:50:13.495644Z",
                "ocflVersion": "v2"
            }, {
                "mementoTimestamp": "20250128110543",
                "mementoDateTime": "2025-01-28T11:05:43.435376Z",
                "ocflVersion": "v3"
            }],
            "archivalGroup": "https://fedora-dev.dlip.digirati.io/fcrepo/rest/chrisrosie-testing/ilkley-meeting/talking-to-jodie"
        },
        "origin": "s3://dlip-pres-dev-fedora/initial/eb4/b73/204/eb4b73204253a2a919e5dea4c08fac287956e388fc5459323cef6f953ac40293",
        "containers": [{
            "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/objects",
            "type": "Container",
            "name": "objects",
            "containers": [{
                "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/objects/folder-b",
                "type": "Container",
                "name": "folder b",
                "containers": [{
                    "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/objects/folder-b/folder-bb",
                    "type": "Container",
                    "name": "folder bb",
                    "containers": [],
                    "binaries": [{
                        "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/objects/folder-b/folder-bb/minutes-laqm-22-april-2020.pdf",
                        "type": "Binary",
                        "name": "MINUTES LAQM 22 April 2020.pdf",
                        "origin": "s3://dlip-pres-dev-fedora/initial/eb4/b73/204/eb4b73204253a2a919e5dea4c08fac287956e388fc5459323cef6f953ac40293/v1/content/objects/folder-b/folder-bb/minutes-laqm-22-april-2020.pdf",
                        "contentType": "application/pdf",
                        "size": 429051,
                        "digest": "310fa7a479e0d0f79caf21e6a2c607e81bb0ccd5c2829bff7b816a49925419e7",
                        "created": "2025-01-27T11:47:34.79295Z",
                        "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
                        "lastModified": "2025-01-27T11:47:34.79295Z",
                        "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
                    }],
                    "created": "2025-01-27T11:47:34.599695Z",
                    "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
                    "lastModified": "2025-01-27T11:47:34.599695Z",
                    "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
                }],
                "binaries": [],
                "created": "2025-01-27T11:47:34.526119Z",
                "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
                "lastModified": "2025-01-27T11:47:34.526119Z",
                "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
            }],
            "binaries": [{
                "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/objects/minutes-laqm-21-june-2020.pdf",
                "type": "Binary",
                "name": "Minutes LAQM 21 June 2020.pdf",
                "origin": "s3://dlip-pres-dev-fedora/initial/eb4/b73/204/eb4b73204253a2a919e5dea4c08fac287956e388fc5459323cef6f953ac40293/v1/content/objects/minutes-laqm-21-june-2020.pdf",
                "contentType": "application/pdf",
                "size": 761611,
                "digest": "eb634d64ce8e6be5195174ceaef9ac9e19c37119f3b31618630aa633ccdbf68f",
                "created": "2025-01-27T11:47:35.323606Z",
                "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
                "lastModified": "2025-01-27T11:47:35.323606Z",
                "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
            }, {
                "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/objects/minutes-laqm-8-sept-2020.pdf",
                "type": "Binary",
                "name": "MINUTES LAQM 8 Sept 2020.pdf",
                "origin": "s3://dlip-pres-dev-fedora/initial/eb4/b73/204/eb4b73204253a2a919e5dea4c08fac287956e388fc5459323cef6f953ac40293/v1/content/objects/minutes-laqm-8-sept-2020.pdf",
                "contentType": "application/pdf",
                "size": 169046,
                "digest": "9c5aa04a39812c80bcc824e366044c16fb090efb076c8552ca9ca932f0dfc981",
                "created": "2025-01-27T11:47:35.545189Z",
                "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
                "lastModified": "2025-01-27T11:47:35.545189Z",
                "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
            }],
            "created": "2025-01-27T11:47:34.338612Z",
            "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
            "lastModified": "2025-01-27T11:47:34.338612Z",
            "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
        }],
        "binaries": [{
            "id": "https://preservation-dev.dlip.digirati.io/repository/chrisrosie-testing/ilkley-meeting/talking-to-jodie/mets.xml",
            "type": "Binary",
            "name": "mets.xml",
            "origin": "s3://dlip-pres-dev-fedora/initial/eb4/b73/204/eb4b73204253a2a919e5dea4c08fac287956e388fc5459323cef6f953ac40293/v3/content/mets.xml",
            "contentType": "application/xml",
            "size": 5474,
            "digest": "1a2b0bcd368f98015530670eed7978233be747ef7a25934e4eab4f05d55bd831",
            "created": "2025-01-28T11:05:42.525188Z",
            "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
            "lastModified": "2025-01-28T11:05:42.525188Z",
            "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
        }],
        "created": "2025-01-27T11:47:34.198612Z",
        "createdBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev",
        "lastModified": "2025-01-27T11:47:34.234776Z",
        "lastModifiedBy": "https://preservation-dev.dlip.digirati.io/agents/dlipdev"
    }