"""
A deposit for an existing object, without exporting its files.

POST to /deposits (not /deposits/export) with the archivalGroup of an object that already exists,
and you get a deposit whose workspace holds only the object's METS file. No waiting: copying one
document is quick, so the deposit is at status `new` straight away.

That one file is enough. The METS knows about every file in the object, with the digests and names
the Archival Group already holds, so a diff can tell that the files you did not upload are still
part of the object rather than things you want deleted.

Set DOCS_ARCHIVAL_GROUP to the path (under /repository) of an object you are allowed to work on.

  python -m p10_exports.mets_only_deposit
"""
import os

import s3_helpers
import settings
from p10_exports.find_archival_group import preserved_archival_group
from preservation import get, post, pprint

archival_group = preserved_archival_group()
print(f"Exporting {archival_group}")

r = post("/deposits", {
    "type": "Deposit",
    "template": "RootLevel",
    "archivalGroup": archival_group,
    "submissionText": "METS-only deposit made by the documentation samples",
})
if r.status_code != 201:
    pprint(r.json())
    raise SystemExit(f"Deposit not created: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]

print(f"\nDeposit {slug}")
print(f"  status              : {deposit['status']}")
print(f"  archivalGroupExists : {deposit['archivalGroupExists']}")
print(f"  files               : {deposit['files']}")

print("\nWhat actually arrived in the workspace:")
s3_helpers.list_keys(deposit["files"])

# The METS is there, and the API has parsed it: every file of the object is listed, with digests,
# even though none of those files are in the workspace.
mets = get(f"/deposits/{slug}/parsed-mets").json()
print(f"\nThe METS describes {len(mets['files'])} file(s) of the object:")
for file in mets["files"][:10]:
    print(f"  {file['localPath']}  {file['size']} bytes  {(file['digest'] or '')[:12]}…")
if len(mets["files"]) > 10:
    print(f"  … and {len(mets['files']) - 10} more")

print(f"\nEditable by the platform: {mets['editable']} (agent: {mets['agent']})")
print("Now upload only the files you are changing, bring the METS into line, and run an Import Job.")
