# Ad hoc deposit, no EMu - with notes

DLIP-UI is talking to an internal API separate from the storage API. This extra participant not shown in this view, but is called _Preservation API_ in other sequecne diagrams when it appears. The DLIP UI is a client of this API but so are other potential applications. The Preservation API is in turn a client of the Storage API. The preservation API is home to concepts such a deposit, and the workflow around building up a deposit, and collaborating on it with others.

![diagram](./create-deposit-with-notes-1.png)

## Notes

1. This user might be an external depositor. Or perhaps an external depositor has already been assigned a deposit to work in? 
2. This identifier is for the job/deposit/working-set-of-files; it is not the EMu id nor is it necessarily the last path element of the eventual location of the Archival Group in Fedora. TBC - if you later export a digital object from Preservation, is it the same row? Is it the same deposit? No, it's a new row with a new ID. So this DB row represents the working set of files for a deposit. See [Pull from Repository](pull-from-repository.md)
3. Here we adopt a convention for file layout, with METS in the root and an `/objects` or `/contents` folder for the files. We have to allow for the possibility that the deposit already has a METS file that we didn't make.
4. See [deposits.sql](../schema/deposits.sql).
5. The loop in this diagram shows the assembly of a digital object. There is an implied API that user actions cause the DLIP UI to call. We don't know quite what that is yet - it's not the same as the Storage API - but it will be possible for other applications to call it, not just the web application DLIP UI. 
6. The **model** for the deposit is more than just the files and folders. This model can be represented in METS. But how is this METS model updated as the deposit is assembled? Do we want to have DB rows (see [files.sql](../schema/files.sql)), or is that unnecessary? Are there fields such as `notes` that are part of the deposit model as it is worked on but are not persisted to METS? Or do we use METS for everything? Are there things we would want in a files table in DB for querying on for reporting purposes, that would be difficult or inefficient to gather from METS files?
7. Invoke processing which will add further information to METS. How often is this run? Not on every file change/addition. Now we have pipelined updating the model, and user action (adding more files) updating the model, and that user action might trigger more pipeline invocation... so we need to work out how to orchestrate all this activity. Especially if the persistence for all this information is a METS file.
8. This user is probably staff.
9. See [ImportJob](https://github.com/digirati-co-uk/uol-leeds-experiments/blob/main/LeedsExperiment/Preservation/ImportJob.cs)