"""
Preserve a new version with an Import Job you wrote yourself.

End to end: create a deposit, put one file in it at a path of your choosing, and POST a job that
says exactly what to do with it. No diff is requested at all.

The Binary's `id` is where the file will live in the Archival Group; its `origin` is where the
bytes are now. They need not correspond, which is what makes this worth doing: you can replace one
file deep in a large object without reproducing its path in the deposit.

  python -m workflows.w05_custom_import_job

Set DOCS_ARCHIVAL_GROUP to the path under /repository of an object w02 preserved, and
DOCS_TARGET_BINARY to the path within it of the Binary to patch.
"""
import os

import s3_helpers
import settings
from preservation import get, post, pprint, wait_for_value
from workflows.own_mets import content_type_of

REPLACEMENT = "sample_files/notes.txt"

path = os.environ.get("DOCS_ARCHIVAL_GROUP", f"{settings.DOCS_CONTAINER_PATH}/w02-first-time")
target = os.environ.get("DOCS_TARGET_BINARY", "objects/about.txt")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{path}"

# ---------------------------------------------------------------------------
# 1. A deposit to run the job from. It gives the job a context and an audit trail; nothing more is
#    needed from it, so no template and no export.
# ---------------------------------------------------------------------------
r = post("/deposits", {
    "type": "Deposit",
    "template": "None",
    "archivalGroup": archival_group,
    "submissionText": f"Replacing {target} with a hand-written Import Job",
})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Deposit not created: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]

# ---------------------------------------------------------------------------
# 2. Upload the replacement, at whatever path suits you.
# ---------------------------------------------------------------------------
origin = s3_helpers.upload_file(deposit["files"], REPLACEMENT, "replacement.txt")

# ---------------------------------------------------------------------------
# 3. Write the job. Everything the platform would have worked out from a METS has to be stated:
#    digest, size and content type, and whether this is an update.
# ---------------------------------------------------------------------------
job = {
    "id": f"https://example.org/my-own-identifier-for-this-job/{slug}",
    "type": "ImportJob",
    "deposit": deposit["id"],
    "archivalGroup": archival_group,
    "isUpdate": True,
    "source": deposit["files"],
    "binariesToPatch": [
        {
            "id": f"{archival_group}/{target}",
            "type": "Binary",
            "name": target.rsplit("/", 1)[-1],
            "origin": origin,
            "contentType": content_type_of(REPLACEMENT),
            "size": s3_helpers.size_of_file(REPLACEMENT),
            "digest": s3_helpers.sha256_of_file(REPLACEMENT),
        }
    ],
}
pprint(job)

# Nothing checks that the object's METS still agrees with this. A real client patching content
# would patch the METS in the same job - see w04, which does it the other way round and lets the
# diff work the operations out.

r = post(f"/deposits/{slug}/importjobs", job)
if r.status_code != 201:
    # 400: no `deposit`, the wrong `deposit`, or an origin outside this deposit's files area.
    pprint(r.json())
    raise SystemExit(f"Import Job not accepted: {r.status_code}")

# ---------------------------------------------------------------------------
# 4. Poll as usual.
# ---------------------------------------------------------------------------
result_id = r.json()["id"].rstrip("/").rsplit("/", 1)[-1]
final = wait_for_value(f"/deposits/{slug}/importjobs/results/{result_id}", "status", "completed",
                       interval=3, retries=40)
if final is None:
    pprint(get(f"/deposits/{slug}/importjobs/results/{result_id}").json())
    raise SystemExit("The Import Job has not completed.")

print(f"\n{final['sourceVersion']} -> {final['newVersion']}")
print(f"Patched: {[binary['id'] for binary in final['binariesPatched']]}")
print(f"The result records the job we submitted as: {final['importJob']}")
