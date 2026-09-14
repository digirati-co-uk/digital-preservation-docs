"""
Asking the platform to run the characterization tools over a deposit.

A pipeline run puts Brunnhilde (which runs Siegfried for format identification and ClamAV for
virus scanning) and ExifTool over everything in objects/, writes what they found into the
deposit's metadata/ folder, and then adds the objects to the METS with that metadata attached.

Two things to know before running this:

  * Lock the deposit first. POST .../pipeline only checks that nobody ELSE holds the lock; it
    does not take one. And when the run finishes it RELEASES the lock, whether or not it was
    the one that took it - so do not expect to still be holding it afterwards.
  * The run deletes everything under metadata/ except metadata/ad-hoc before it uploads its own
    output. Tool output you placed there by hand will not survive.
"""
import time

from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, post, pprint

TERMINAL = ("completed", "completedWithErrors")

deposit = ensure_deposit()
slug = deposit_slug(deposit)

# Which jobs are there already? We need this to tell the new one apart from earlier runs.
before = {job["jobId"] for job in get(f"/deposits/{slug}/pipelinerunjobs").json()}

post(f"/deposits/{slug}/lock")          # 204, or 409 if someone else has it
post(f"/deposits/{slug}/pipeline")      # 204 and nothing else; the work happens elsewhere

# 404 no such deposit; 409 locked by someone else; 400 the deposit is not in the working bucket
# the pipeline can reach.

# The job appears in the list as "waiting" more or less immediately; it may be a few seconds.
job = None
for _ in range(15):
    new = [j for j in get(f"/deposits/{slug}/pipelinerunjobs").json() if j["jobId"] not in before]
    if new:
        job = new[0]
        break
    time.sleep(2)

print(f"\nPipeline job {job['jobId']} is {job['status']}")

# waiting -> processing -> metadataCreated -> completed | completedWithErrors.
# How long this takes is a function of how much is in objects/: minutes for a handful of files,
# hours for a large deposit, because every file is scanned by ClamAV.
while job["status"] not in TERMINAL:
    time.sleep(10)
    job = get(f"/deposits/{slug}/pipelinerunjobs/{job['jobId']}").json()
    print(f"  {job['status']}")

pprint(job)

if job["status"] == "completedWithErrors":
    # errors is a list of error objects, each with a message - not a list of strings.
    for error in job["errors"] or []:
        print(f"ERROR: {error['message']}")
    raise SystemExit(1)

# The run has already added the objects to the METS, so the metadata the tools produced is
# visible on each file. Refresh first: the pipeline wrote to S3 behind the API's back.
filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()


def files_in(directory, found=None):
    found = found if found is not None else []
    found.extend(directory["files"])
    for child in directory["directories"]:
        files_in(child, found)
    return found


print("\nWhat the tools found:")
for file in files_in(filesystem):
    if not file["localPath"].startswith("objects/"):
        continue
    print(f"\n{file['localPath']}")
    for metadata in file.get("metadata") or []:
        kind, source = metadata["type"], metadata["source"]
        if kind == "FileFormatMetadata":
            print(f"  {kind} ({source}): {metadata['pronomKey']} {metadata['formatName']}")
        elif kind == "VirusScanMetadata":
            found = metadata["virusFound"] or "nothing"
            print(f"  {kind} ({source}): {found}, definitions {metadata['virusDefinition']}")
        elif kind == "ExifMetadata":
            print(f"  {kind} ({source}): {len(metadata['tags'])} tags")
        else:
            print(f"  {kind} ({source})")

# The lock has already been released by the pipeline. Take it again if you want to carry on
# working on this deposit undisturbed.
