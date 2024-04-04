# Deposit with Catalogue Record

> If there is an EMu item for this thing, enter its ID. The app pulls in some details from EMu here to make it easier to identify this thing; “all relevant system IDs”. Can I do it the other way – create an EMu record for the whole object? Probably not. Maybe later.

Need to assign corresponding EMu id at start, or during, a process. You may know what it is at start, you may know later, it may never have an EMu id. 

This sequence occurs during the user interaction in [Create Deposit](create-deposit-with-notes.md).

```mermaid
sequenceDiagram
    actor A as Staff
    participant UI as DLIP UI
    participant API as Preservation API
    participant EMu
    participant ID as ID Minter

    A->>UI: Set EMu ID
    UI->>API: AssociateEMu()
    activate API
    note right of API: What is the role of ID minter?<br>Do we tell it we have just made<br>this association?
    API-->>ID: Any comms here?
    API->>EMu: Fetch Metadata
    API->>API: Update METS
    note right of API: We only want minimal information.<br>Set the title, provide some info for METS.
    note right of API: This will also update the deposit row in the DB
    deactivate API
```