# Create deposit from external file set

Show that we provide a separate API to PUT files to S3 (eg Goobi can do this)

> I can ask that the Preservation Service fetches the files from a provided location. S3 bucket initially, ambient access; we don’t mind how the files got there and they might just be raw files or they might be a BagIt layout (we try to detect this). Can add more sources as needed.

## External process PUT-ting files

Is this what Goobi is doing?

NB the details of interaction with storage are omitted, see [Create Deposit](create-deposit-with-notes.md)


```mermaid
sequenceDiagram
    participant External as External Process
    participant API as Preservation API
    participant ID as ID Minter
    participant S3 as S3 Working
    participant Pipe as Pipelines
    participant Storage as Storage API

    External->>API: Create new Deposit
    activate API
    API->>ID: Obtain Deposit ID
    API->>S3: Create working area
    deactivate API

    note right of External: The external process now has<br>a root URL it can PUT files to    
    loop assemble digital object
        External->>API: PUT binary with sha256 in header
        activate API
        API->>S3: store at path
        deactivate API
        note right of API: create the S3 path for a PUT<br>if path doesn't exist
        note right of External: What additional info with each PUT?<br>Are we just recreating Fedora API here?
    end
    External->>API: Preserve() (see note)
    activate API
    note right of API: METS is created - optionally.<br>The object might already have METS.
    API->>Pipe: Run pipelines
    note right of API: METS is updated by processes.<br>Also optional, may already have all it needs.
    API->>Storage: Import Job (see Create Deposit)
    deactivate API

```

### Notes

Here the External API is just making PUTs, but it could use the Preservation API to work on the files. It MUST supply a checksum.

The Preserve action takes different options:

 - The Repository path where the digital object should be stored
 - Whether to create a METS file from the structure. The caller might have already provided a METS file. It's possible we might want to create our own METS file too, or alternatively we know we can work with the caller's METS file (e.g., the caller is Goobi)
 - Which pipelines, if any, to run. Again, 
 - Whether we should try to update an existing third party METS file with pipeline outputs, or write to our own METS file. Perhaps this is rare or even non-existent - maybe we only run pipelines when the output is going into our own METS. 

## Fetch a BagIt Bag

In the above flow the external process was driving the deposit - creating a new deposit, PUTting binaries one at a time, then completing the process.

In the following flow, the external process just tells the Preservation API (not the Storage API) that there is a set of files waiting _somewhere_ - typically S3 - and that it should create and preserve a deposit from them. The Preservation API detects that the external location contains a BagIt bag, with checksums etc. It doesn't just reproduce the BagIt inside Fedora, it turns the BagIt into a digital object.

We could create METS just from the BagIt, but we run the standard pipelines anyway. This verifies that checksums in the BagIt metadata are still correct. The BagIt bag is just a different way of supplying the checksums.


```mermaid
sequenceDiagram
    participant External as External Process
    participant API as Preservation API
    participant ID as ID Minter
    participant Stage as S3 Staging
    participant S3 as S3 Working
    participant Pipe as Pipelines
    participant Storage as Storage API

    External->>Stage: (1) Save a BagIt bag to a staging location
    note right of External: This might have been done<br>from a BitCurator environment.
    External->>API: Preserve()
    activate API
    API->>Stage: Analyse file layout
    API->>API: BagIt detected
    API->>ID: Obtain Deposit ID
    API->>S3: Create working area
    note right of API: METS is created (?)
    loop assemble working files
    API->>S3: Copy from stage S3 to working
    end
    API->>Pipe: Run pipelines
    note right of API: METS is updated by processes
    API->>API: Validate()
    note right of API: Validate SHA256 from BagIt against SHA256 from pipeline
    API->>Storage: Import Job (see Create Deposit)
    deactivate API
```

## Notes

Some processes may be able to put this directly, but we also might offer an upload for this. E.g., visit the Preservation UI from inside a BitCurator environment and upload the bag.