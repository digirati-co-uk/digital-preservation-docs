# Database and METS usage

One thing that characterises the Preservation API when compared to the Storage API is that it needs some kind of queryable persistence to manage the activity of deposits and use of Storage API. It needs to keep track of jobs. The Storage API, and Fedora behind it, are about Archival Groups. The Storage API doesn't care what's in the Archival Group, it has no meaning. The Presentation API does understand the content - as far as METS model, anyway. And it can manage the process of getting the content from users and external systems into the Storage API through the concept of a _deposit_.

[Deposits table](../schema/deposits.sql.md)

It's not clear whether we would also need a files table:

[Files table](../schema/files.sql.md)

And we probably need to record invocations of pipelines:

[Pipeline jobs table](../schema/pipeline_jobs.sql.md)




```mermaid
sequenceDiagram
    actor A as Actor
    participant API as Preservation API
    participant DB as Database    
    participant ID as ID Minter
    participant S3 as S3 Working
    participant Storage as Storage API

    A-->>API: Create new Deposit
    activate API
    note left of API: User doesn't directly call API<br>of course - this is just a detail
    API->>ID: Obtain Deposit ID
    Note left of ID: (2) We ask the ID service for<br>a deposit ID, e.g., a56fzc8w
    API->>DB: Create DB row in deposits
    Note left of S3: (3) We use that ID to create a "folder"<br> - S3 key is that ID in a flat structure.
    API->>S3: Create working area
    deactivate API

    
    A-->>API: Recent activity
    activate API
    API->>DB: GET last 10 deposits for user
    deactivate API

    
    A-->>API: Run pipeline (e.g., file format)
    activate API
    API->>DB: Record details, start and end
    deactivate API

    A-->>API: Preserve
    activate API
    API->>Storage: Preserve, get version info, etc
    API->>DB: Update deposit
    deactivate API

```


See Fedora-Usage-Principles.docx