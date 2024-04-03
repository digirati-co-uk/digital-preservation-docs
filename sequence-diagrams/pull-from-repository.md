# Pull from repository (export)

Can this be drop-boxy - don't actually fetch all the files, just make stub keys in S3 from the METS file AND correlate to the Fedora OCFL object

... need to be VERY careful!

Must never write a stub back by mistake.

We only fetch the actual binary from S3 if you want to see it. (what happens then - how do you "see" it? - download? download streams from S3 origin in OCFL)

This is the default - mode=stub - see note 3 below. But I might want to export the full object, all the binaries intact, for some other purpose, so I can optionally use mode=full.

-	At any point, even long after it is preserved, I can pull an object out of preservation and update granular permissions. Typically this only changes a METS file. (impl – are we resuscitating DB rows to do this so we can re-make a METS file?)

```mermaid
sequenceDiagram

    actor A as User
    participant UI as DLIP UI
    participant API as Preservation API
    participant ID as ID Minter
    participant S3 as S3 Working
    participant Storage as Storage API
    participant Fedora

    A->>UI: Browse
    note left of UI: find Archival Group
    A->>UI: Export AG
    UI->>API: Export AG
    API->>ID: (1) Obtain ID
    note right of API: API creates a new row in deposits
    API->>S3: (2) Create working area
    API->>Storage: (3) Export, mode=stub
    Storage->>Fedora: (4) (OCFL locations)
    Storage->>S3: Copy METS in full from fedora origin
    note left of Storage: We need the METS<br>to be our model
    loop 
    Storage->>S3: Create keys for containers
    Storage->>S3: Create stub keys for binaries
    end
    A->>UI: Browse exported "deposit"
    note right of A: User finds the file they are interested in
    A->>UI: Download
    UI->>API: Download
    API->>Storage: Copy binary
    Storage->>S3: (copy from fedora origin)
    note left of Storage: binary is now in S3
    S3->>UI: Stream from S3
    UI->>A: (has file)
```