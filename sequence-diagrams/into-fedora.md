# Content into Fedora

- There is a `preservation_path` property of a deposit which can be applied at any time. And may have been automatically assigned and might not be editable for some users. It's the Fedora path this deposit will end up at. An HTTP(S) URI.

- After the preservation step, ALL working files are hard-deleted from the working space. This includes uploaded things that we decided not to push to preservation.

- I want to specify a publication date at which time a job is pushed to Fedora

- I can control WHEN synchronisation with asset delivery happens. For Goobi, the mechanism will be same as Wellcome, put a msg on a queue; for Preservation UI – as soon as preserved; or on a schedule (on this date?)

```mermaid
sequenceDiagram
    actor A as Actor
    participant API as Preservation API
    participant DB as Database
    participant ID as ID Minter
    participant S3 as S3 Working
    participant Storage as Storage API
    participant Fedora
    participant IIIF-C

    note left of API: This is the last step in a deposit
    A->>API: Set preservation_path
    activate API
    API->>DB: Update deposit
    deactivate API
    A->>API: Preserve
    activate API
    API->>ID: Tell ID service about preservation_path
    API->>Storage: Prepare import job
    API->>Storage: Submit import job
    deactivate API
    activate Storage
    critical Within Fedora transaction
        Storage->>Fedora: Create Archival Group
        Storage->>Fedora: Create Containers
        Storage->>Fedora: Create Binaries
        Fedora->>S3: Read binary content
    end
    Storage->>API: Callback? Message on Queue?
    deactivate Storage
    activate API
    API->>S3: Clean up, delete workspace
    API->>DB: Update deposit
    deactivate API