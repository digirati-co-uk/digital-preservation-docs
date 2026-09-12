"""
Deleting a deposit: the way to abandon a piece of work, or start it again.

This removes the Deposit record AND empties its workspace in S3. It does nothing to an Archival
Group already created from the deposit - that is preserved, and lives in OCFL.
"""
import sys

from preservation import delete, get

if len(sys.argv) < 2:
    print("Usage: python -m p04_deposits.delete_deposit <deposit-id>")
    sys.exit(1)

slug = sys.argv[1]
deposit = get(f"/deposits/{slug}").json()
print(f"About to delete {deposit['id']} ({deposit['status']}), workspace {deposit['files']}")

# 409 Conflict if someone else holds the lock; 204 No Content on success.
r = delete(f"/deposits/{slug}")
print(r.status_code)

get(f"/deposits/{slug}")   # 404: a deposit is not a preserved resource, so it leaves no tombstone
