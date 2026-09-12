"""
Every attempt made from one deposit.

A bare JSON array, oldest first - not a page object, and with no query parameters. Usually it has
nothing or one entry in it: a deposit whose job succeeded can't be used for another. More than one
means earlier attempts that ended in `completedWithErrors`, which don't count against the deposit.

  python -m p09_import_job_results.list_results
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get

deposit = ensure_deposit()
slug = deposit_slug(deposit)

results = get(f"/deposits/{slug}/importjobs/results").json()
print(f"\n{len(results)} Import Job result(s) for deposit {slug}")

for result in results:
    print(f"\n  {result['id']}")
    print(f"    submitted {result['created']} by {result['createdBy']}")
    print(f"    status    {result['status']}")
    print(f"    versions  {result['sourceVersion']} -> {result['newVersion']}")
    print(f"    job       {result['importJob']}")
    if result.get("originalImportJob"):
        print(f"    asked as  {result['originalImportJob']}")
    for error in result.get("errors") or []:
        print(f"    ERROR     {error['message']}")

# This listing is the API's stored copy of each result, refreshed when an individual result is
# fetched or when its background reader catches up. For the live state of a running job, GET its id.
