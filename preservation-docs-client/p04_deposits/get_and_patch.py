"""
Fetching a deposit, and changing the three things that can be changed.

Fetching is not passive: the API re-checks whether the Archival Group exists, re-reads the METS
ETag, and moves a finished export from "exporting" to "new".
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, patch, pprint

deposit = ensure_deposit()
slug = deposit_slug(deposit)

deposit = get(f"/deposits/{slug}").json()
print(f"{deposit['status']}, active={deposit['active']}, "
      f"archivalGroupExists={deposit['archivalGroupExists']}")

# Only archivalGroup, archivalGroupName and submissionText can be patched. Send just the ones
# you are changing; anything else in the body is ignored.
patched = patch(f"/deposits/{slug}", {
    "type": "Deposit",
    "archivalGroupName": "A better name",
    "submissionText": "I changed my mind about the name.",
}).json()

pprint({k: patched[k] for k in ["archivalGroupName", "submissionText", "lastModified", "lastModifiedBy"]})
