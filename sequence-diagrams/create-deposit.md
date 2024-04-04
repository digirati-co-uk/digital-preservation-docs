# Ad hoc deposit, no EMu

DLIP-UI is talking to an internal API separate from the storage API. This extra participant not shown in this view, but is called _Preservation API_ in other sequecne diagrams when it appears. The DLIP UI is a client of this API but so are other potential applications. The Preservation API is in turn a client of the Storage API. The preservation API is home to concepts such a deposit, and the workflow around building up a deposit, and collaborating on it with others.

The Upload Component is running in the user's browser to manage the bulk upload of files. It's part of the DLIP UI Web Application, aka Deposit Service. 

```mermaid
sequenceDiagram
    actor A as Staff
    box Client App
    participant UP as Upload Component
    participant UI as DLIP UI
    end
    participant ID as ID Minter
    participant S3 as S3 Working
    participant Storage as Storage API
    participant Fedora
    
    A->>UI: Create new Deposit
    UI->>ID: Obtain Deposit ID
    UI->>S3: Create working area
    loop assemble digital object
        A->>UP: Select files and folders
        UP->>UP: Generate checksums (browser)
        UP->>UI: Upload files
        UI->>S3: Save files in working area
    end
    A->>UI: Save to Preservation
    UI->>UI: Prepare Update Job
    UI->>Storage: Submit Update Job
    critical Within Fedora transaction
        Storage->>Fedora: Create Archival Group
        Storage->>Fedora: Create Containers
        Storage->>Fedora: Create Binaries
        Fedora->>S3: Read binary content
    end
```