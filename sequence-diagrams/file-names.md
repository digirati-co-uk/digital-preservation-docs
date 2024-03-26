# File names and normalisation

Even files uploaded from a computer or collected from S3 may contain invalid paths.

The spreadsheet view shows original and normalised (highlight where different)

Also allows you to edit original names.

 - The UI presents a folder and file layout. You can see all the accumulated technical metadata that machines have extracted, but can’t edit it. You can edit access conditions and rights, hierarchically. Both of these are just strings from controlled vocabs (drop-downs). You can apply them at any level and override them below that. Do this in a METS-sensible way. The meanings of these strings is realised in asset delivery, but also (maybe) in who can see objects in the Preservation UI. A special case is opening up one object to one user (sharing progress of a deposit).