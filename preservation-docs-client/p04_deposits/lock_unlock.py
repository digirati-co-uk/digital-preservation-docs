"""
Locks. A lock is a marker, not a barrier: you can still write to the workspace in S3, because
the API cannot see that. What it does do is refuse API operations on the deposit - patching,
deleting, editing the METS - to anyone who is not the lock holder.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import delete, get, post

deposit = ensure_deposit()
slug = deposit_slug(deposit)

post(f"/deposits/{slug}/lock")           # 204; the caller becomes lockedBy
locked = get(f"/deposits/{slug}").json()
print(f"lockedBy={locked['lockedBy']} lockDate={locked['lockDate']}")

# A second caller would get 409 Conflict here. They can insist:
post(f"/deposits/{slug}/lock?force=true")

delete(f"/deposits/{slug}/lock")         # 204; anyone may remove a lock
unlocked = get(f"/deposits/{slug}").json()
print(f"lockedBy={unlocked['lockedBy']}")

delete(f"/deposits/{slug}/lock")         # unlocking an unlocked deposit is a no-op, not an error
