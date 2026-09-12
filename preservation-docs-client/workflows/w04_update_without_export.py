"""
Preserve a new version without exporting the object's files.

End to end: create a deposit against an existing Archival Group with a plain POST to /deposits -
which copies only the METS - upload the one file that is changing, bring the METS into line, check
that the diff is not about to delete everything, and preserve.

The point of the exercise is step 5: the diff knows about every file in the object, from the METS,
even though almost none of them are in the workspace.

  python -m workflows.w04_update_without_export

Set DOCS_ARCHIVAL_GROUP to the path under /repository of an object w02 preserved.
"""
import os

import s3_helpers
import settings
from preservation import get, post, pprint, wait_for_value
from workflows.own_mets import build_mets

NEW_FILE = ("sample_files/about.txt", "objects/docs/added-by-w04.txt")

path = os.environ.get("DOCS_ARCHIVAL_GROUP", f"{settings.DOCS_CONTAINER_PATH}/w02-first-time")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{path}"

# ---------------------------------------------------------------------------
# 1. A plain deposit against an existing Archival Group. No export, no waiting: only the METS is
#    copied in, and the deposit comes back at status `new`.
# ---------------------------------------------------------------------------
r = post("/deposits", {
    "type": "Deposit",
    "template": "RootLevel",
    "archivalGroup": archival_group,
    "submissionText": "Adding one file, without exporting the rest",
})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Deposit not created: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nDeposit {slug}, status '{deposit['status']}', "
      f"archivalGroupExists {deposit['archivalGroupExists']}")

print("\nWhat actually arrived in the workspace:")
s3_helpers.list_keys(deposit["files"])

# ---------------------------------------------------------------------------
# 2. The METS, however, knows about the whole object.
# ---------------------------------------------------------------------------
parsed = get(f"/deposits/{slug}/parsed-mets").json()
existing = [
    {
        "local_path": file["localPath"],
        "size": file["size"],
        "digest": file["digest"],
        "name": file.get("name"),
        "content_type": file.get("contentType"),
    }
    for file in parsed["files"]
    if "/" in file["localPath"]          # the METS file itself is in the root; skip it
]
print(f"\nThe METS describes {len(existing)} file(s) of the object.")

# ---------------------------------------------------------------------------
# 3. Upload only what is changing.
# ---------------------------------------------------------------------------
local_path, relative_path = NEW_FILE
s3_helpers.upload_file(deposit["files"], local_path, relative_path, with_checksum=True)

# ---------------------------------------------------------------------------
# 4. Bring the METS into line: everything it already described, plus the new file.
# ---------------------------------------------------------------------------
described = existing + [{
    "local_path": relative_path,
    "size": s3_helpers.size_of_file(local_path),
    "digest": s3_helpers.sha256_of_file(local_path),
}]
mets = build_mets(parsed["name"] or "A tiny sample object", described)
s3_helpers.upload_text(deposit["files"], mets, "mets.xml", content_type="application/xml")

# ---------------------------------------------------------------------------
# 5. Read the diff before running it. One binary to add, one to patch (the METS), and - the part
#    worth checking - nothing to delete.
# ---------------------------------------------------------------------------
r = get(f"/deposits/{slug}/importjobs/diff")
if r.status_code != 200:
    pprint(r.json())
    raise SystemExit(f"No diff: {r.status_code}")

job = r.json()
for operation in ["containersToAdd", "binariesToAdd", "containersToDelete", "binariesToDelete",
                  "binariesToPatch", "containersToRename", "binariesToRename"]:
    print(f"  {operation}: {[entry['id'].rsplit('/', 1)[-1] for entry in job[operation]]}")

if job["binariesToDelete"] or job["containersToDelete"]:
    raise SystemExit("The diff wants to delete things. Stop and work out why before preserving.")

# ---------------------------------------------------------------------------
# 6. Run it and wait.
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

print(f"\n{final['sourceVersion']} -> {final['newVersion']}, "
      f"having uploaded one file instead of the whole object")
