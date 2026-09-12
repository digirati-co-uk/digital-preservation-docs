"""
Waiting for an Import Job to finish.

The result is returned as soon as the job is accepted, long before it runs. You poll its `id` until
`status` is `completed` or `completedWithErrors`. You don't have to: a background process in the
Preservation API brings its records up to date about once a minute either way. Polling just makes it
happen sooner, and gives you somewhere to put the error handling.

Run p08_import_jobs/execute_diff.py first, or set DOCS_DEPOSIT_ID to a deposit that has one.

  python -m p09_import_job_results.poll_result
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, pprint, wait_for_value

deposit = ensure_deposit()
slug = deposit_slug(deposit)

results = get(f"/deposits/{slug}/importjobs/results").json()
if not results:
    raise SystemExit("No Import Job has been run from this deposit. Run p08_import_jobs.execute_diff.")

# Oldest first, so the last one is the attempt we care about.
result_id = results[-1]["id"].rstrip("/").rsplit("/", 1)[-1]

# waiting -> running -> completed (or completedWithErrors)
final = wait_for_value(f"/deposits/{slug}/importjobs/results/{result_id}", "status", "completed",
                       interval=3, retries=40)

if final is None:
    latest = get(f"/deposits/{slug}/importjobs/results/{result_id}").json()
    pprint(latest)
    raise SystemExit(f"Gave up waiting; status is '{latest['status']}'")

print(f"\n{final['sourceVersion']} -> {final['newVersion']}")
print(f"Began {final['dateBegun']}, finished {final['dateFinished']}")

for operation in ["containersAdded", "binariesAdded", "containersDeleted", "binariesDeleted",
                  "binariesPatched", "containersRenamed", "binariesRenamed"]:
    entries = final[operation]
    if entries:
        print(f"\n{operation}: {len(entries)}")
        for entry in entries:
            print(f"  {entry['id']}")

# A job that fails reports it here rather than as an HTTP error - the request returned long before.
if final.get("errors"):
    for error in final["errors"]:
        print(f"ERROR {error.get('id') or ''} {error['message']}")

# The deposit has moved on too: preserved (or error), and inactive either way.
refreshed = get(f"/deposits/{slug}").json()
print(f"\nDeposit status: {refreshed['status']}, version preserved: {refreshed['versionPreserved']}")
