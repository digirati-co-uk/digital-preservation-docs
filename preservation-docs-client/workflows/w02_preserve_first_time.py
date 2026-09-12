"""
Preserve a digital object for the first time, supplying your own METS file.

End to end: create a deposit, upload two files and a METS document that describes them, point the
deposit at a place in the repository, run the Import Job, and wait for v1.

Nothing on the METS-editing side of the API is used here. The platform reads this METS - for the
digests, names and content types the Import Job needs - but never writes to it.

  python -m workflows.w02_preserve_first_time

The Container the object goes into must already exist; see p03_repository/create_and_delete_container.py.
"""
import os

import s3_helpers
import settings
from preservation import get, post, pprint, wait_for_value
from workflows.own_mets import build_mets

SAMPLE_FILES = [
    ("sample_files/about.txt", "objects/about.txt"),
    ("sample_files/notes.txt", "objects/docs/notes.txt"),
]

name = os.environ.get("DOCS_ARCHIVAL_GROUP_NAME", "w02-first-time")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{settings.DOCS_CONTAINER_PATH}/{name}"

# ---------------------------------------------------------------------------
# 1. Create a Deposit. No template: we are supplying the METS, so we don't want one written for us.
# ---------------------------------------------------------------------------
r = post("/deposits", {
    "type": "Deposit",
    "template": "None",
    "archivalGroup": archival_group,
    "archivalGroupName": "A tiny sample object",
    "submissionText": "Created by the documentation workflow samples",
})
if r.status_code != 201:
    # 409 here usually means there is already an active deposit for this Archival Group.
    pprint(r.json())
    raise SystemExit(f"Deposit not created: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nDeposit {slug}, workspace {deposit['files']}")

# ---------------------------------------------------------------------------
# 2. Upload the files, and build a METS file describing exactly what we uploaded.
#
# ChecksumAlgorithm SHA256 asks S3 to store a digest as well. It is not required when the METS
# supplies one, but if both are present the platform checks that they agree - and a disagreement
# is a refused Import Job rather than a corrupt object.
# ---------------------------------------------------------------------------
described = []
for local_path, relative_path in SAMPLE_FILES:
    s3_helpers.upload_file(deposit["files"], local_path, relative_path, with_checksum=True)
    described.append({
        "local_path": relative_path,
        "size": s3_helpers.size_of_file(local_path),
        "digest": s3_helpers.sha256_of_file(local_path),
    })

mets = build_mets("A tiny sample object", described)
s3_helpers.upload_text(deposit["files"], mets, "mets.xml", content_type="application/xml")

# ---------------------------------------------------------------------------
# 3. Check that the platform can read it before asking for the Import Job.
# ---------------------------------------------------------------------------
parsed = get(f"/deposits/{slug}/parsed-mets").json()
print(f"\nThe platform read the METS as '{parsed['name']}', {len(parsed['files'])} file(s), "
      f"agent '{parsed['agent']}', editable by the platform: {parsed['editable']}")

# ---------------------------------------------------------------------------
# 4. Generate and run the Import Job in one action.
# ---------------------------------------------------------------------------
r = post(f"/deposits/{slug}/importjobs", {"id": f"/deposits/{slug}/importjobs/diff"})
if r.status_code != 201:
    # 422 means the METS and the workspace disagree - a file missing from one or the other,
    # or a digest, size or content type that doesn't match.
    pprint(r.json())
    raise SystemExit(f"Import Job not accepted: {r.status_code}")

result = r.json()
result_id = result["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nImport Job result {result_id}, status '{result['status']}'")

# ---------------------------------------------------------------------------
# 5. Poll until it has finished.
# ---------------------------------------------------------------------------
final = wait_for_value(f"/deposits/{slug}/importjobs/results/{result_id}", "status", "completed",
                       interval=3, retries=40)
if final is None:
    pprint(get(f"/deposits/{slug}/importjobs/results/{result_id}").json())
    raise SystemExit("The Import Job has not completed.")

print(f"\nPreserved as {final['newVersion']}: "
      f"{len(final['containersAdded'])} container(s), {len(final['binariesAdded'])} binary/binaries")

# ---------------------------------------------------------------------------
# 6. Load the Archival Group. Unlike an ordinary Container, this comes back complete: every
#    descendant Container and Binary, however deep.
# ---------------------------------------------------------------------------
archival_group_json = get(archival_group).json()
print(f"\n{archival_group_json['id']}")
print(f"  name    : {archival_group_json['name']}")
print(f"  version : {archival_group_json['version']['ocflVersion']}")

print("\nTo use this object in the update workflows, set:")
print(f"  DOCS_ARCHIVAL_GROUP={settings.DOCS_CONTAINER_PATH}/{name}")
