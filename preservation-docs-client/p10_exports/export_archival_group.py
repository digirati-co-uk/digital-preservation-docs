"""
Getting the files of a preserved object back out.

You have no access to the repository storage, so to work with an object's files you export it into
a new deposit. The POST returns immediately with a deposit at status `exporting`; the files are not
all there until it reaches `new`.

Fetching the deposit is what moves it on: there is no background process watching exports, so the
API checks with the Storage API when you ask for the deposit, and promotes it then.

Set DOCS_ARCHIVAL_GROUP to the path (under /repository) of an object you are allowed to export.

  python -m p10_exports.export_archival_group
"""
import os

import s3_helpers
import settings
from preservation import post, pprint, wait_for_value

path = os.environ.get("DOCS_ARCHIVAL_GROUP", f"{settings.DOCS_CONTAINER_PATH}/import-job-example")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{path}"

r = post("/deposits/export", {
    "type": "Deposit",
    "archivalGroup": archival_group,
    # "versionExported": "v2",   # omit for the latest version
})
if r.status_code != 201:
    # 400: no archivalGroup, or nothing there to export.
    # 409: there is already an active deposit for this Archival Group.
    pprint(r.json())
    raise SystemExit(f"Export not accepted: {r.status_code}")

deposit = r.json()
slug = deposit["id"].rstrip("/").rsplit("/", 1)[-1]
print(f"\nDeposit {slug} is at status '{deposit['status']}', exporting version "
      f"{deposit['versionExported']}")

# exporting -> new. Every GET of the deposit asks the Storage API whether the copy has finished,
# and promotes the deposit when it has - so this loop is causing the transition, not just watching.
deposit = wait_for_value(f"/deposits/{slug}", "status", "new", interval=5, retries=60)
if deposit is None:
    raise SystemExit("The export has not finished; try again, or look at the deposit in the UI.")

print(f"\nExport finished. Files are in {deposit['files']}")
s3_helpers.list_keys(deposit["files"])

print("\nThe deposit is now an ordinary working area: change the files, update the METS, and run")
print("an Import Job to preserve the next version. If you only wanted to read the files, DELETE")
print("the deposit when you have finished - an abandoned export blocks anyone else from making")
print("a deposit for the same Archival Group.")
