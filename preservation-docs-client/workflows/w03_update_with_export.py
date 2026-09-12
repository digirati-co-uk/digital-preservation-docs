"""
Preserve a new version, after exporting the whole object.

End to end: export an Archival Group into a new deposit, wait for every file to arrive, add one
more file, rewrite the METS to describe the new state, and preserve.

The export is the expensive part - every binary in the object is copied into the deposit's area in
S3. Do this when you need the whole object in front of you. When you already know what you are
changing, w04_update_without_export.py is the same job without the copying.

  python -m workflows.w03_update_with_export

Set DOCS_ARCHIVAL_GROUP to the path under /repository of an object w02 preserved.
"""
import os

import s3_helpers
import settings
from preservation import get, post, pprint, wait_for_value
from workflows.own_mets import build_mets, files_from_filesystem

NEW_FILE = ("sample_files/notes.txt", "objects/docs/added-by-w03.txt")

path = os.environ.get("DOCS_ARCHIVAL_GROUP", f"{settings.DOCS_CONTAINER_PATH}/w02-first-time")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{path}"

# ---------------------------------------------------------------------------
# 1. Create the export. Add "versionExported": "v2" to work from an older version.
# ---------------------------------------------------------------------------
r = post("/deposits/export", {
    "type": "Deposit",
    "archivalGroup": archival_group,
})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Export not accepted: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nDeposit {slug}, exporting {deposit['versionExported']}, status '{deposit['status']}'")

# ---------------------------------------------------------------------------
# 2. Wait for the files. Fetching the deposit is what checks the export and moves it on to `new`.
# ---------------------------------------------------------------------------
deposit = wait_for_value(f"/deposits/{slug}", "status", "new", interval=5, retries=60)
if deposit is None:
    raise SystemExit("The export has not finished.")

print("\nThe workspace now holds:")
s3_helpers.list_keys(deposit["files"])

# ---------------------------------------------------------------------------
# 3. Change the files. Here: add one.
# ---------------------------------------------------------------------------
local_path, relative_path = NEW_FILE
s3_helpers.upload_file(deposit["files"], local_path, relative_path, with_checksum=True)

# ---------------------------------------------------------------------------
# 4. Rewrite the METS so that it describes the object as it now is.
#
# The file system view gives the digest, size and content type of everything in the workspace -
# including the files that came out of the repository - so the whole document can be rebuilt from
# it. A real client with a more complicated METS would edit the document rather than regenerate it.
# ---------------------------------------------------------------------------
filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()
described = files_from_filesystem(filesystem)
print(f"\nRewriting the METS to describe {len(described)} file(s)")

mets = build_mets(deposit["archivalGroupName"] or "A tiny sample object", described)
s3_helpers.upload_text(deposit["files"], mets, "mets.xml", content_type="application/xml")

# ---------------------------------------------------------------------------
# 5. Look at the diff before running it. This is a real diff against the existing object: anything
#    in the Archival Group that is no longer here would be listed for deletion.
# ---------------------------------------------------------------------------
job = get(f"/deposits/{slug}/importjobs/diff").json()
print(f"\nisUpdate {job['isUpdate']}, from version {job['sourceVersion']['ocflVersion']}")
for operation in ["containersToAdd", "binariesToAdd", "containersToDelete", "binariesToDelete",
                  "binariesToPatch", "containersToRename", "binariesToRename"]:
    if job[operation]:
        print(f"  {operation}: {[entry['id'].rsplit('/', 1)[-1] for entry in job[operation]]}")

# ---------------------------------------------------------------------------
# 6. Run it, exactly as it came back, and wait.
# ---------------------------------------------------------------------------
r = post(f"/deposits/{slug}/importjobs", job)
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Import Job not accepted: {r.status_code}")

result_id = r.json()["id"].rstrip("/").rsplit("/", 1)[-1]
final = wait_for_value(f"/deposits/{slug}/importjobs/results/{result_id}", "status", "completed",
                       interval=3, retries=40)
if final is None:
    pprint(get(f"/deposits/{slug}/importjobs/results/{result_id}").json())
    raise SystemExit("The Import Job has not completed.")

print(f"\n{final['sourceVersion']} -> {final['newVersion']}")
