"""
Running the job.

Two ways to do it, and this sample shows both. The second one - POSTing a body that is nothing but
the diff URI - tells the API to generate the diff and run it in one action, which closes the window
in which the deposit could change between your looking at it and your submitting it.

This preserves a real object. Once it succeeds the deposit is finished: `active` becomes false and
no further Import Job can be run from it.

  python -m p08_import_jobs.execute_diff
"""
from p04_deposits.ensure_deposit import deposit_slug
from p08_import_jobs.ready_deposit import ready_deposit
from preservation import get, post, pprint

deposit = ready_deposit()
slug = deposit_slug(deposit)

# 1. Post the whole job, exactly as the diff returned it.
#
#     job = get(f"/deposits/{slug}/importjobs/diff").json()
#     r = post(f"/deposits/{slug}/importjobs", job)
#
# 2. Or post a reference to the diff, and let the API generate it at the moment it runs.
#
# The value must end with the path you are POSTing to plus "/diff", and the comparison is
# case-sensitive - so use the lower-case /importjobs path, as here.
r = post(f"/deposits/{slug}/importjobs", {
    "id": f"/deposits/{slug}/importjobs/diff",
})

if r.status_code != 201:
    # 400: the job doesn't belong to this deposit, or a binary origin is outside its files area.
    # 409: the deposit is locked by someone else, or another job for this Archival Group is running.
    pprint(r.json())
    raise SystemExit(f"Not accepted: {r.status_code}")

result = r.json()
pprint(result)

print(f"\nStatus is '{result['status']}'; the job has been queued, not run.")
print(f"Poll {result['id']} to watch it - see p09_import_job_results/poll_result.py")

refreshed = get(f"/deposits/{slug}").json()
print(f"Deposit status is now: {refreshed['status']}, active: {refreshed['active']}")
