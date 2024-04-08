# Multiple actors

Multiple staff picking up processes

External donors being involved

How do we lock?
What do we lock?

Leave notes on individual files and folders. Some actors may be allowed to do this but not do anything else. - file open
Move stuff around - this is more restricted. - structure locked

Do file notes imply DB table [files](../schema/files.sql.md)? 
Do they live in METS?
Do we throw them away afterwards? (after preservation?)

Leave notes for people - other staff members, donors, anyone you send a sharing link to
Checkboxes per file / folder for workflow collaboration.

-	I can share a job with a donor / other staff member, even opening up just that one job. Anyone can leave notes on any file or folder. There are a fixed set of flags that can be set by various parties, these appear as checkboxes

Multiple staff members can pick up the same process

-	Implies a set of processes in motion... pigeonholes again?
-	Do they need to be locked? Or are they stateful so doesn’t matter who triggers a move?

-	As a potential depositor (donor), not a staff member, I can be given a login to a system that is focused only on me providing my files with no distractions. I can upload, I can take my time, I can come back the next day, I can remove things I’ve uploaded by mistake, I can see the folder and file layout, I can add notes to folders and files. At the start of this process there is a form to fill in that establishes consent / agreements etc. This lives with the deposit throughout its journey. This is not Archivematica for real.

- There is an audit trail for any creation of sharing links, and access to sharing links by staff or external actors.

-	When I’m ready I can submit the object. After that I can’t edit – I can’t delete files for example – but I can participate in a process with an archivist or digital preservation person; we can look at it together.

-	As a () I can create a sharing link that allows access to a particular file, or a folder of files, or a whole digital object. The sharing link has time limits and will expire after the period I specify. I can use this to send files to customers who have made a digitsation request, too – even if it’s a digitised workflow from Goobi.

> We need a safe environment to view and share sensitive and protected access material, for users that have been cleared and for staff.

To what extent do we need to transcode content for people to view in ad hoc preservation UI environment? Public-facing content, even where that "public" is a very small group of staff users, will go via the IIIF Cloud Services. But while the material is being worked on, while it's maybe not even yet in Fedora, people still need to preview it.

For images, we could have a separate, stream-only Cantaloupe instance (like IIIF-C's SpecialServer) that can see the S3 Working area. This would be quite slow for deep zoom, but doesn't really need tile delivery, it's OK with larger JPEGs. For AV though - how do we offer web-accessible versions from here? For sharing etc.