"""
Asking the API what it would do.

A diff Import Job is a GET: it changes nothing, it just compares the deposit's files (and the METS
that describes them) with the current state of the Archival Group, and says what would have to
happen to make the one match the other. Read it before you run it.

  python -m p08_import_jobs.get_diff
"""
from p04_deposits.ensure_deposit import deposit_slug
from p08_import_jobs.ready_deposit import ready_deposit
from preservation import get, pprint

deposit = ready_deposit()
slug = deposit_slug(deposit)

r = get(f"/deposits/{slug}/importjobs/diff")
if r.status_code != 200:
    # 400: no archivalGroup, or the deposit is still exporting.
    # 409: this deposit has already had an Import Job run from it, or a digest disagrees.
    # 422: a file in the deposit is missing from the METS, or has no digest there.
    pprint(r.json())
    raise SystemExit(f"No diff: {r.status_code}")

job = r.json()

print(f"\nArchival Group : {job['archivalGroup']}")
print(f"Is an update   : {job['isUpdate']}")
print(f"Source version : {job['sourceVersion']}")   # an object, not a string; null for a new object
print(f"Source         : {job['source']}")

for operation in ["containersToAdd", "binariesToAdd", "containersToDelete", "binariesToDelete",
                  "binariesToPatch", "containersToRename", "binariesToRename"]:
    entries = job[operation]
    print(f"\n{operation}: {len(entries)}")
    for entry in entries:
        print(f"  {entry['id']}")
        if entry.get("origin"):
            print(f"    from {entry['origin']}")
        if entry.get("digest"):
            print(f"    {entry['contentType']}, {entry['size']} bytes, sha256 {entry['digest'][:12]}…")

# `id` is transient - asking again produces a different one. `originalId` is the stable diff URI,
# and it is what you POST back as a diff reference (see execute_diff.py).
print(f"\nid         : {job['id']}")
print(f"originalId : {job['originalId']}")
