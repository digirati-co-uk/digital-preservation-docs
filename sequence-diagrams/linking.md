# Linking deposits

I can create a digital object without an EMu ID and link it to another object (which may or may not have an EMu ID) via an adjunct relationship.  “link digital files to catalogue records even if they are not the born-digital file”. 

This new object may also have come about by [splitting](splitting.md) another digital object.

It should be the responsibility of the Preservation API to tell the id service about the relationship, but not to manage the data for the relationship.

```mermaid
sequenceDiagram

actor A as Actor
participant UI as DLIP UI + Pres.API
participant ID as ID Service

A->>UI: User is looking at object A
A->>UI: User finds object B and copies its Fedora path
note right of UI: maybe in another tab
A->>UI: User clicks "link..." on object A
A->>UI: User pastes path and provides relationship type
note right of UI: We have a controlled vocabulary (dropdown)<br>for the different types of link allowed.
UI->>ID: API tells ID Service about the relationship
note right of UI: Source, target, link type

note right of A: (Later...)
A->>UI: View object A
UI->>ID: Get all related identifiers
UI->>UI: Render links to Object B (as well as EMu, public web page and more)
A->>UI: User can navigate to related things
```