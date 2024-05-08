# Splitting Deposits, and multiple EMu records

What begins as one digital object may need to be split into two or more separate objects (e.g., appraisal suggests the need to treat one accessioned set of files as distinct digital objects).

These digital objects may be associated with different EMu records.

- [Export metadata to EMu](export-metadata.md) shows how one digital object can generate multiple child records in EMu.

This use case is different:

- One of the new objects may keep the EMu identifier previously held by the original
- The new object(s) may be assigned new independent EMu identifiers as in [Deposit with Catalogue Record](calling-emu.md)
- One or more of the new objects may not have an EMu identifier at all
- The new object(s) may share an accession identifier with the original objects

## One digital object, multiple EMu records

We can see that this is already possible from the parent/child relationship in - [Export metadata to EMu](export-metadata.md). That assigns identity to files within a digital object. But is is possible / desirable that two or more _sibling_ (or even less closely related) EMu records have a digital counterpart that is in fact the same _digital_ object?

_(Going to use a non born digital item to make the use case more obvious)_

An example of this may be a photo album, perhaps with correspondence glued onto its pages. It makes sense for the user experience of the OBJECT (as a IIIF Manifest, typically) to persist as the "object in hand" - the whole album. But the photographs or letters within may be significant enough to be catalogued in great detail, as siblings in a series.

This _might_ be no different from the [Export metadata to EMu](export-metadata.md) parent child relationship, it just comes about in a different way (the distinct EMu records already existed before the album was digitised). 

We just need to make sure that all possibilities are catered for in our workflow.