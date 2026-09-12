# Site plan: page slugs (all agents must use exactly these file names so cross-links work)

Link form: sibling page `../slug`; other group `../../group/slug`; anchor `#heading`.

## introduction/
1 quickstart.mdx       - Two shortest paths to a preserved object: own METS, and platform-managed
2 overview.mdx        - What the platform is, who the docs are for, the stack diagram
3 concepts.mdx        - Archival Group, Container, Binary, Deposit, METS, Import Job, versions, OCFL, activity stream
4 components.mdx      - OCFL, Fedora, Storage API, Preservation API, Preservation UI, Pipeline API, iiif-builder, IIIF Cloud Services

## preservation-api/
1  overview.mdx                    - hosts, JSON conventions, common metadata, permitted characters, error object, whoami
2  authentication.mdx              - Entra ID client credentials, bearer token, X-Client-Identity, local DisableAuth
3  repository.mdx                  - Container/Binary/ArchivalGroup, browsing, view/version params, HEAD, PUT/DELETE Container, content endpoint, validation endpoint
4  deposits.mdx                    - create, templates, from-identifier, get, list/query, patch, delete, activate/deactivate, lock/unlock, deposit lifecycle/status
5  deposit-files.mdx               - filesystem & combined views; WorkingDirectory, WorkingFile, MetsExtensions, Metadata types
6  editing-mets.mdx                - GET mets, parsed-mets, POST mets (add), mets/delete, mets/normalise, If-Match/ETag
7  libraries.mdx                    - WorkspaceManager and the METS libraries; where the API ends
8  tool-outputs-and-pipelines.mdx  - tool output locations table, POST pipeline, pipelinerunjobs, ProcessPipelineResult, what the pipeline does
9  import-jobs.mdx                 - diff, ImportJob properties, execute, the diff-id shortcut body
10 import-job-results.mdx          - ImportJobResult, polling, listing
11 exports.mdx                     - POST deposits/export, empty deposit for existing AG, deposit archive jobs (if applicable)
12 activity-stream.mdx             - OrderedCollection/pages, processing algorithm, POST push (if for external use)
13 versions-and-storage-map.mdx    - versions, ocfl/storagemap, version object, relation to OCFL
14 search.mdx
15 iiif.mdx                        - deposit as IIIF Manifest, AG as IIIF Manifest, iiif-token, media endpoint, POST manifest back (logical structMaps)
16 vocabularies.mdx                - access-conditions, range-types
17 agents.mdx                      - agents list, agent URIs, whoami

## workflows/
1 overview.mdx
2 recipes.mdx          - Small answers to specific questions
2 preserve-first-time.mdx        - own METS, first version (from 06 quickstart)
3 update-with-export.mdx
4 update-without-export.mdx
5 custom-import-job.mdx
6 managed-mets-deposit.mdx       - RootLevel template, upload files, run pipeline, add to METS, import
7 bagit-deposit.mdx
8 reading-the-activity-stream.mdx

## mets/
1 overview.mdx           - the platform's use of METS; map of the four pages (from 02a + intro material)
2 mets-we-write.mdx      - from 02b
3 mets-we-read.mdx       - from 02c
4 identifiers.mdx        - from 02d
5 editability.mdx        - from 02e

## ui/
1 overview.mdx
2 browsing.mdx           - Browse page, archival group view, binary view, OCFL page
3 deposits.mdx           - deposits list, creating a deposit (DepositNew), the Deposit page: files, upload, METS editing, metadata, pipeline
4 import-jobs.mdx        - import job page, running, results
5 search-and-changes.mdx - Search, Changes (activity), Status pages

## storage-api/
1 overview.mdx           - what it is, who can call it, where it differs from Preservation API
2 import.mdx             - POST /import, results, test-path
3 export.mdx             - POST /export, GET /export/{id}, export mets only
4 activity-and-content.mdx - activity stream of import jobs, /content binary retrieval, storagemap, search

## (not on the site)

`internals/` in the repository root - overview, pipeline-api, deployment - as plain markdown.
Different audience (people who run the platform, not people who use it) and a different rate of
change, especially once backends other than S3 arrive. iiif-builder is not documented at all: Leeds
run their own version now. WorkspaceManager moved onto the site as `preservation-api/libraries.mdx`,
because an API caller does want it.
