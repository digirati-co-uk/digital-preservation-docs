# Flat view and Directory view

## Tree view

A hierarchical, "explorer" view of files and folders (containers and binaries in Fedora terms) within the digital object (archival group).

This view is easier for inheriting, ACL-like access conditions - assign an access condition to a whole folder, for example.

## Flat view

Flat view is like a spreadsheet, easier to see normalised name vs folder name.

Allows sorting and filtering, e.g., on Access Condition.

You can assign rights statements and access conditions in either view.


```mermaid
sequenceDiagram
    actor A as User
    participant UI as DLIP UI
    participant API as Preservation API

    A->>UI: Select tree view
    loop tasks easier in hierarchy
    A->>UI: Assign rights statement(s)
    A->>UI: Assign access conditions
    UI-->API: (update METS)
    end

    A->>UI: Select flat view
    loop tasks easier in table
    A->>UI: Check filenames
    A->>UI: Assign individual access conditions
    UI-->API: (update METS)
    end
```

