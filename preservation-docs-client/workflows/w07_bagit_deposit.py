"""
Depositing a BagIt bag.

End to end: create a BagIt-layout deposit, upload a tiny unpacked bag into it, add the payload to
the METS, and look at the diff - where the `data/` prefix appears in the `origin` of every Binary
and in none of the `id`s.

The bag here is generated rather than read from disk, so that the sample has nothing to carry
around: two payload files, a bagit.txt, a bag-info.txt and a sha256 manifest.

  python -m workflows.w07_bagit_deposit
"""
import os
from datetime import datetime, timezone

import s3_helpers
import settings
from preservation import get, post, pprint, wait_for_value

PAYLOAD = [
    ("sample_files/about.txt", "objects/about.txt"),
    ("sample_files/notes.txt", "objects/docs/notes.txt"),
]

name = os.environ.get("DOCS_ARCHIVAL_GROUP_NAME", "w07-bagit")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{settings.DOCS_CONTAINER_PATH}/{name}"

# ---------------------------------------------------------------------------
# 1. A BagIt-layout deposit: the same scaffolding as RootLevel, one level down inside data/.
# ---------------------------------------------------------------------------
r = post("/deposits", {
    "type": "Deposit",
    "template": "BagIt",
    "archivalGroup": archival_group,
    "archivalGroupName": "A tiny bag",
    "submissionText": "Created by the documentation workflow samples",
})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Deposit not created: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nDeposit {slug}, workspace {deposit['files']}")

# ---------------------------------------------------------------------------
# 2. Upload the bag: payload under data/, tag files in the root.
# ---------------------------------------------------------------------------
manifest_lines = []
for local_path, relative_path in PAYLOAD:
    s3_helpers.upload_file(deposit["files"], local_path, f"data/{relative_path}")
    # BagIt manifest paths are relative to the bag root, so they include data/.
    manifest_lines.append(f"{s3_helpers.sha256_of_file(local_path)}  data/{relative_path}")

s3_helpers.upload_text(deposit["files"], "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n",
                       "bagit.txt")
s3_helpers.upload_text(deposit["files"],
                       f"Bagging-Date: {datetime.now(timezone.utc).date()}\n"
                       f"Source-Organization: Documentation samples\n",
                       "bag-info.txt")
s3_helpers.upload_text(deposit["files"], "\n".join(manifest_lines) + "\n", "manifest-sha256.txt")

# The platform reads manifest-sha256.txt and uses its digests as a source of SHA256 for the
# payload, alongside the METS and S3 object metadata.

# ---------------------------------------------------------------------------
# 3. Work with paths as they appear BELOW data/. The file system view is the layout on disk, so it
#    shows data/ - but every path you give the API omits it.
# ---------------------------------------------------------------------------
filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()


def paths_in(directory, found=None):
    found = found if found is not None else []
    for file in directory["files"]:
        found.append(file["localPath"])
    for child in directory["directories"]:
        paths_in(child, found)
    return found


print("\nOn disk:")
for path in sorted(paths_in(filesystem)):
    print(f"  {path}")

to_add = [relative_path for _, relative_path in PAYLOAD]      # no data/ prefix
print(f"\nAdding to the METS: {to_add}")
# Fetch the deposit for its metsETag. Neither the response to creating a deposit nor the deposit
# listing carries one - only GET /deposits/{id} does.
deposit = get(f"/deposits/{slug}").json()
r = post(f"/deposits/{slug}/mets", to_add, extra_headers={"If-Match": deposit["metsETag"]})
if r.status_code >= 400:
    pprint(r.json())
    raise SystemExit(f"Could not add to METS: {r.status_code}")

# ---------------------------------------------------------------------------
# 4. The diff. ids have no data/; origins do; the tag files are nowhere to be seen.
# ---------------------------------------------------------------------------
r = get(f"/deposits/{slug}/importjobs/diff")
if r.status_code != 200:
    pprint(r.json())
    raise SystemExit(f"No diff: {r.status_code}")

job = r.json()
print(f"\nsource: {job['source']}")
for binary in job["binariesToAdd"]:
    print(f"  id     {binary['id']}")
    print(f"  origin {binary['origin']}")

if any("/data/" in binary["id"] for binary in job["binariesToAdd"]):
    raise SystemExit("Unexpected: data/ has leaked into the repository paths.")
if any("bagit.txt" in binary["id"] for binary in job["binariesToAdd"]):
    raise SystemExit("Unexpected: a BagIt tag file is being preserved.")

# ---------------------------------------------------------------------------
# 5. Preserve.
# ---------------------------------------------------------------------------
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

print(f"\nPreserved as {final['newVersion']}. The Archival Group is indistinguishable from one")
print("deposited in the RootLevel layout: the bag was packaging, and packaging is not preserved.")
