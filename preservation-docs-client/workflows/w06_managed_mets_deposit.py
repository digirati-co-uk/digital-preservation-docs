"""
A deposit whose METS the platform manages.

End to end: create a deposit from the RootLevel template, upload files, run the characterisation
pipeline over them, push what the tools found into the METS, and preserve.

The contrast with w02 is that no XML is written here. The platform scaffolds the METS, and the
`.../mets` endpoint adds each file to it along with all the metadata collected for that file.

  python -m workflows.w06_managed_mets_deposit
"""
import os
import time

import s3_helpers
import settings
from preservation import get, post, pprint, wait_for_value

SAMPLE_FILES = [
    ("sample_files/about.txt", "objects/about.txt"),
    ("sample_files/notes.txt", "objects/docs/notes.txt"),
]

name = os.environ.get("DOCS_ARCHIVAL_GROUP_NAME", "w06-managed-mets")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{settings.DOCS_CONTAINER_PATH}/{name}"

# ---------------------------------------------------------------------------
# 1. A templated deposit. The workspace arrives with objects/, metadata/ad-hoc/ and an empty
#    mets.xml that the platform wrote - and may therefore edit.
# ---------------------------------------------------------------------------
r = post("/deposits", {
    "type": "Deposit",
    "template": "RootLevel",
    "archivalGroup": archival_group,
    "archivalGroupName": "A managed-METS sample object",
    "submissionText": "Created by the documentation workflow samples",
})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Deposit not created: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nDeposit {slug}, workspace {deposit['files']}")
s3_helpers.list_keys(deposit["files"])

# ---------------------------------------------------------------------------
# 2. Upload the files. No checksums needed: the pipeline produces them.
# ---------------------------------------------------------------------------
for local_path, relative_path in SAMPLE_FILES:
    s3_helpers.upload_file(deposit["files"], local_path, relative_path)

# ---------------------------------------------------------------------------
# 3. Run the pipeline. 204 No Content - the work is queued, not done.
# ---------------------------------------------------------------------------
r = post(f"/deposits/{slug}/pipeline")
if r.status_code != 204:
    pprint(r.json())
    raise SystemExit(f"Pipeline not started: {r.status_code}")

# ---------------------------------------------------------------------------
# 4. Wait for it. waiting -> processing -> metadataCreated -> completed. `metadataCreated` means
#    the tools have run but their output has not yet been put back into the deposit, so it is not
#    the state to stop at.
# ---------------------------------------------------------------------------
for attempt in range(60):
    jobs = get(f"/deposits/{slug}/pipelinerunjobs").json()
    status = jobs[-1]["status"] if jobs else "(none yet)"
    print(f"Pipeline status: {status}")
    if status in ("completed", "completedWithErrors"):
        break
    time.sleep(5)
else:
    raise SystemExit("The pipeline has not finished.")

if status == "completedWithErrors":
    pprint(jobs[-1])
    raise SystemExit("The pipeline reported errors.")

# ---------------------------------------------------------------------------
# 5. The file system view now carries what the tools found - but the METS is still empty.
# ---------------------------------------------------------------------------
filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()


def files_in(directory, found=None):
    found = found if found is not None else []
    for file in directory["files"]:
        found.append(file)
    for child in directory["directories"]:
        files_in(child, found)
    return found


all_files = files_in(filesystem)
for file in all_files:
    sources = sorted({entry["source"] for entry in file.get("metadata") or []})
    print(f"  {file['localPath']}  {sources}")

mets = get(f"/deposits/{slug}/parsed-mets").json()
print(f"\nThe METS currently describes {len(mets['files'])} file(s) "
      f"(the METS itself); editable: {mets['editable']}")

# ---------------------------------------------------------------------------
# 6. Push the files - and their metadata - into the METS. Only paths in or below objects/ or
#    metadata/ are added; parent folders are created for you. If-Match guards the write.
# ---------------------------------------------------------------------------
to_add = [file["localPath"] for file in all_files
          if file["localPath"].startswith(("objects/", "metadata/"))]
deposit = get(f"/deposits/{slug}").json()
r = post(f"/deposits/{slug}/mets", to_add, extra_headers={"If-Match": deposit["metsETag"]})
if r.status_code >= 400:
    # 409 means the METS has changed since we last read its ETag.
    pprint(r.json())
    raise SystemExit(f"Could not add to METS: {r.status_code}")
pprint(r.json())

# ---------------------------------------------------------------------------
# 7. Check the deposit and the METS agree, then preserve.
# ---------------------------------------------------------------------------
get(f"/deposits/{slug}/combined")
print("\nThe combined view is the deposit's files and the METS merged - exactly what the diff is")
print("computed from. Anything in the deposit but not the METS would stop it. Now preserving.")

r = post(f"/deposits/{slug}/importjobs", {"id": f"/deposits/{slug}/importjobs/diff"})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Import Job not accepted: {r.status_code}")

result_id = r.json()["id"].rstrip("/").rsplit("/", 1)[-1]
final = wait_for_value(f"/deposits/{slug}/importjobs/results/{result_id}", "status", "completed",
                       interval=3, retries=40)
if final is None:
    pprint(get(f"/deposits/{slug}/importjobs/results/{result_id}").json())
    raise SystemExit("The Import Job has not completed.")

print(f"\nPreserved as {final['newVersion']}, with characterisation metadata inside the METS.")
