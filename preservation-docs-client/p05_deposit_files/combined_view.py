"""
Deposit and METS side by side.

The platform merges the two into a "combined directory" and works from that - it is how the diff
Import Job knows what to add and what to leave alone. The combined endpoint itself is a debugging
aid and produces a great deal of JSON, so this sample does the same comparison from the two
ordinary views instead.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get

deposit = ensure_deposit()
slug = deposit_slug(deposit)

filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()
mets = get(f"/deposits/{slug}/parsed-mets").json()


def paths_in(directory, found=None):
    found = found if found is not None else set()
    for file in directory["files"]:
        found.add(file["localPath"])
    for child in directory["directories"]:
        paths_in(child, found)
    return found


in_deposit = paths_in(filesystem)
in_mets = {file["localPath"] for file in mets["files"]}

# The same three states the combined view calls Deposit, Mets and Both.
print("In the deposit but not the METS (candidates to add):")
for path in sorted(in_deposit - in_mets):
    print(f"  {path}")

print("\nIn the METS but not the deposit (normal after an update without a full export):")
for path in sorted(in_mets - in_deposit):
    print(f"  {path}")

print(f"\nIn both: {len(in_deposit & in_mets)}")
print(f"METS is editable by the platform: {mets['editable']} (agent: {mets['agent']})")
