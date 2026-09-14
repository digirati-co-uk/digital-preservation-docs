# Findings: tool outputs and pipelines (brief 4)

Discrepancies between the old documentation, the RFCs, and the code, found while writing
`preservation-api/tool-outputs-and-pipelines.mdx` and `internals/pipeline-api.mdx`.
Each entry says where it was found, what the code actually does, and whether it looks like a
documentation error or a code bug.

Three of these were re-checked directly against the code and hold: the
`metadata/brunnhilde/siegfried.csv` path (and that `report.html` gates the whole folder), the
`metadata/` wipe that a pipeline run performs before uploading, and the unreachable
`InProcessPipelineQueue`. The rest are as the agent reported them.

## Old documentation vs code

- **The Siegfried-via-Brunnhilde path in the old table is wrong.** (tool-outputs page)
  `documentation/02-Preservation-API.md` says `/metadata/brunnhilde/siegfried/siegfried.csv`.
  `DigitalPreservation.Workspace/MetadataReader.cs:104` reads
  `brunnhildeRoot.AppendEscapedSlug("siegfried.csv")` - i.e. `metadata/brunnhilde/siegfried.csv`,
  with no `siegfried/` folder in between. That is also where Brunnhilde itself puts it (see the
  worked example in `rfcs/006-pipelines-and-outputs.md#workflow`). **Documentation error**; the
  site uses the real path.

- **The old table omits two tool outputs entirely.** (tool-outputs page) `MetadataReader` also
  reads `metadata/exif/exif_output.txt` (line 547 -> `ExifMetadata`, source `ExifTool`, plus a
  generated per-file HTML `ToolOutput` with source `Exif`) and
  `metadata/virus-definition/virus-definition.txt` (line 170 -> the `virusDefinition` value on
  every `VirusScanMetadata`). Both are written by Pipeline API on every run
  (`ExecutePipelineJob.cs`; `PipelineToolOptions.PipelineMetadataFolders` in
  `Pipeline.API/appsettings.json` names all three managed folders:
  `metadata/brunnhilde,metadata/exif,metadata/virus-definition`). **Documentation error** -
  incomplete rather than wrong.

- **`metadata/brunnhilde/report.html` is a gate, not just a `ToolOutput` source.** (tool-outputs
  page) `MetadataReader.FindMetadata` probes for `report.html` (lines 99-102) because a folder
  does not exist as an object in S3, and reads `siegfried.csv` and `logs/viruscheck-log.txt`
  **only if the probe succeeds**. A deposit that has the virus log but no `report.html` gets no
  format identification and no virus-scan metadata from the Brunnhilde folder, silently. Not a
  bug exactly - it is a deliberate "does this folder exist" test - but it is undocumented and
  surprising, and worth a comment or a second probe if Brunnhilde's output ever changes shape.

- **Standalone Siegfried output is found more leniently than the old table says.** (tool-outputs
  page) The old table lists exactly `siegfried.yaml`, `siegfried.yml`, `siegfried.csv`.
  `MetadataReader.FindSiegfriedOutput` (line 464) *lists* `metadata/siegfried/` and takes any
  `.yaml`, `.yml` or `.csv` in it; it only narrows to names beginning `siegfried.` when there is
  more than one candidate. So a single `metadata/siegfried/output.yaml` is read. It also parses
  by content, not extension - a `.csv` that fails CSV parsing is retried as YAML
  (`ParseSiegfriedOutput`, line 420). **Documentation error**, on the cautious side.

- **"For a deposit whose METS file is not managed by the platform, files under metadata/ are
  ignored and not processed" is false.** (tool-outputs page) `MetadataReader.Create` is called
  from `GetWorkingDirectory` (`DigitalPreservation.Workspace/Requests/GetWorkingDirectory.cs`,
  lines 23/33/42) on every refresh of the deposit file system, with no reference to the METS
  agent or `Editable`. Tool outputs in a third-party-METS deposit **are** read and **do** appear
  in the `metadata` of each `WorkingFile`. What cannot happen is the platform writing them into
  a METS it did not author. **Documentation error**; the site says what is actually true.

- **The Deposit example in the old doc carries `"pipelineJobs": []`.** Already recorded in
  `findings.md` from the deposits page; confirmed again here. Pipeline results are only at
  `GET /deposits/{id}/pipelinerunjobs`. Documentation error.

- **The old `ProcessPipelineResult` table omits `deposit`, `cleanupProcessJob` and
  `virusDefinition`.** (tool-outputs page) All three are serialised -
  `DigitalPreservation.Common.Model/PipelineApi/ProcessPipelineResult.cs`. See the next entry for
  the last two. Documentation error.

- **The old doc gives no HTTP status codes for `POST /deposits/{id}/pipeline`.** The controller
  declares 204/400/404/401/409 (`DepositsController.cs:499`) and `RunPipelineHandler` produces
  `NotFound`, `Conflict` (deposit locked by someone else) and `BadRequest` (deposit not in the
  default working bucket). Documented on the site.

## Code observations (not documentation errors)

- **`ProcessPipelineResult.virusDefinition` is always null, and `cleanupProcessJob` always
  false, in API responses.** `Preservation.API/Mutation/ResourceMutator.MutatePipelineRunJob`
  (line 199) never sets either. `VirusDefinition` was added to the `PipelineRunJob` entity by
  migration `20251028094803_AddVirusDefinitionToPipelineJobs` and removed again by
  `20251105142156_RemoveVirusDefinitionFromPipelineJobs`, but the property was left on the
  serialised model. `CleanupProcessJob` is used only inside Pipeline API, as internal control
  flow on the `ProcessPipelineResult` it passes around in-process. Both are dead weight on the
  public JSON. **Looks like a code tidy-up**: either populate them or mark them
  `[JsonIgnore]`. The site documents `virusDefinition` as reserved and currently always null, and
  leaves `cleanupProcessJob` out; the virus definition a caller actually wants is on each file's
  `VirusScanMetadata`.

- **Pipeline API registers two `IPipelineQueue` implementations; the feature flag that looks
  like it chooses between them is never read.** `Pipeline.API/Program.cs` does
  `.AddSingleton<IPipelineQueue, InProcessPipelineQueue>().AddSingleton<IPipelineQueue,
  SqsPipelineQueue>()`, so the last registration wins and `SqsPipelineQueue` is always injected.
  `FeatureFlags:UseLocalHostedServiceForPipeline` is set in all four `appsettings*.json` files
  (`true` in Example and Testing, `false` in the deployed one) but no code anywhere reads it -
  compare `FeatureFlags:UseLocalHostedServiceForImport` in Storage API, which is read. So Pipeline
  API always goes via SNS/SQS, even locally, and `InProcessPipelineQueue` is unreachable dead
  code. **Looks like a code bug** (or at least an abandoned switch): running Pipeline API locally
  without AWS is not possible as the wiring stands. Recorded on the internals page as "always
  SQS".

- **`FeatureFlags:DisableAuth` does nothing in Pipeline API.** Already in `findings.md` from the
  authentication page; re-confirmed. Pipeline API's only gate is `X-API-KEY`.

- **The API key comparison is not constant-time, and a missing header is indistinguishable from
  a wrong one.** `Pipeline.API/Middleware/ApiKeyMiddleware.cs` does `extractedApiKey == apiKey`
  on a `StringValues`. Already recorded as a HIGH in the April 2026 security review; repeated
  here because the internals page documents the mechanism. **Code bug**, low practical risk
  behind a private load balancer.

- **`ApiKeyAttribute` fails open if the middleware is not in the pipeline.** The filter returns
  without doing anything when `HttpContext.Items` has no `ApiKeyValid` entry - the comment says
  "This can be removed once feature flag is removed". If `UseMiddleware<ApiKeyMiddleware>()` were
  ever dropped from `Program.cs`, every endpoint would become anonymous rather than refusing.
  **Code smell**; not documented on the site.

- **`PipelineController.CheckDepositFolderAndContents` takes a caller-supplied `depositId` and
  `Path.Combine`s it onto the mount path, then shells out to `bash -c df`.** Filesystem traversal
  (`?depositId=../..`) and an unnecessary shell invocation, on an endpoint that only exists for
  diagnostics. Both are HIGHs already recorded in the April 2026 security review (filesystem
  traversal in `PipelineController`, the `Bash()` trap). **Code bug**; the internals page
  mentions the endpoint exists but not how to abuse it.

- **`UploadFileToDepositOnS3`'s "is this a Brunnhilde file?" guard only passes by coincidence.**
  `ExecutePipelineJob.cs` skips any upload whose `filePath` does not contain the string
  `"brunnhilde"`. Exif and virus-definition output would fail that test on its own terms - they
  pass only because the process folder is itself called `/usr/process-brunnhilde`
  (`PipelineToolOptions.ProcessFolder`). Renaming that folder in config would silently stop the
  Exif and virus-definition files being uploaded. **Code bug waiting to happen.**

- **`DeleteSelection.ContinueIfFail` is inverted.** Already in `findings.md` from the
  editing-mets page. Its only caller is
  `ExecutePipelineJob.DeleteBrunnhildeFoldersAndFiles`, which passes
  `PipelineToolOptions.PipelineMetadataFolders` - so those three folder paths are the ones whose
  deletion failure is *fatal*, despite the property name.

- **A pipeline run deletes everything under `metadata/` except `metadata/ad-hoc`, from both the
  workspace and the METS, before uploading fresh output.**
  `ExecutePipelineJob.DeleteBrunnhildeFoldersAndFiles` builds a `DeleteSelection` over every
  directory and file whose `localPath` starts with `metadata` and does not start with
  `metadata/ad-hoc`. That is correct and deliberate - a tool output folder holds one set of
  results, not a history (the decision is recorded in `rfcs/006` under "Tool outputs from
  pipelines") - but it is not stated anywhere a caller would look, and it means a hand-placed
  Siegfried output in `metadata/siegfried/` is destroyed by running the pipeline. Documented
  prominently on the tool-outputs page.

## RFCs vs code (RFCs are intent; code wins)

- **RFC 006's proposed layout `metadata/clamAV/virusscan.csv` does not exist.** ClamAV output is
  only ever read from inside Brunnhilde's own folder,
  `metadata/brunnhilde/logs/viruscheck-log.txt`. There is no standalone ClamAV location. Intent
  not implemented; not documented on the site.

- **RFC 006's `IMetsManager.AddFileFormatInformation(Uri yamlFileLocation, OutputMapping?)` was
  never built.** There is no per-tool-output API call. Tool outputs are discovered by convention
  from fixed paths and incorporated when files are added to METS
  (`POST /deposits/{id}/mets`). The path-mapping problem the `OutputMapping` parameter was for is
  solved instead by `MetadataReader.AllowForObjectsAndMetadata`, which finds the common parent of
  the paths a tool reported and trims it back to the deposit root. Intent superseded.

- **RFC 006's timestamped output folders (`metadata/pipelines/{timestamp}/...`) were rejected**, and
  the RFC itself records the decision in a later note. Code agrees: one folder per tool. No
  conflict, noted only because the RFC reads as a live proposal until the note.

- **RFC 006: "the bagit .txt files in the root are copied into a `__bagit/` directory in
  `metadata/` ... (Not yet implemented)."** Still not implemented - nothing in the code writes or
  reads `__bagit`. What *does* happen for a BagIt deposit is that the pipeline re-bags the
  deposit in its own scratch space and uploads the regenerated `bagit.txt`, `bag-info.txt`,
  `manifest-sha256.txt` and `tagmanifest-sha256.txt` back to the **root** of the workspace
  (`UploadBagitFilesToRoot`). Intent not implemented.

- **RFC 006a: "The Preservation API locks the Deposit as pipeline user."** It does not. `POST
  /deposits/{id}/pipeline` checks that nobody *else* holds the lock and then queues the job; it
  never acquires one. The Preservation UI takes the lock itself immediately before calling
  (`Deposit.cshtml.cs:OnPostRunPipeline` sends `LockDeposit` then `RunPipeline`), and Pipeline
  API **releases** the lock at the end of the run whether or not it was the one that took it. An
  API caller who does not lock first therefore gets no protection while the pipeline runs, and a
  caller who does lock first has the lock taken away from them on completion. Intent partly
  implemented, asymmetrically. Documented as it is (lock it yourself first; expect it to be
  released for you), but this is worth a decision: the lock ought to be acquired by whatever
  queues the job.

- **RFC 006a: "The Preservation API refreshes the storage."** Pipeline API does this, not
  Preservation API, and it does more than refresh: it calls the equivalent of
  `POST /deposits/{id}/mets` for every file under `objects/`
  (`ExecutePipelineJob.AddObjectsToMets`), so the objects are added to (or updated in) the METS
  automatically at the end of a run. RFC 006a leaves that as an open question ("The user can
  decide whether to add to METS at this stage (or maybe this happens automatically)"). It happens
  automatically. Documented.

- **RFC 006's "Questions" about ECS vs Fargate and .NET vs Python are settled by the code.**
  Pipeline API is .NET, runs on an EC2-backed ECS cluster (it spawns child processes and needs a
  mounted file system), reads a single SQS queue fed by an SNS topic, and reports status back to
  Preservation API over HTTP rather than via a second "job done" queue. Recorded on the internals
  page as fact.

## Stale code comments

- **`clamscan-shim.sh`'s header comment is stale.** It says it redirects to "the clamd daemon
  running on the EC2 host, reached via the Unix socket bind-mounted into this container". The
  Dockerfile installs `clamav-daemon` in the image and `pipeline-api-entrypoint.sh` starts and
  supervises `clamd` (and `freshclam`) *inside the same container*; the socket never leaves the
  container's namespace, as the Dockerfile's own comment on `LocalSocketMode` says. Presumably
  the design changed and the shim's comment did not follow. **Code comment error**; the internals
  page describes the entrypoint's actual behaviour.
