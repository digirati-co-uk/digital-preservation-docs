"""
Removing things from the METS and the workspace.

deleteFromMets is a modifier, not an alternative: the METS entry goes when the file goes. There is
no operation that takes a file out of the METS while leaving it in the deposit.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, post, pprint

deposit = ensure_deposit()
slug = deposit_slug(deposit)

# Re-read the deposit: the METS ETag changes every time the METS is written, and a stale one is
# a 409 rather than an overwrite.
deposit = get(f"/deposits/{slug}").json()

selection = {
    "deleteFromMets": True,
    "deleteFromDepositFiles": True,
    "items": [
        # isDir is required, not inferred. List child files as well as their folder; the API
        # orders the deletions itself, deepest first.
        {"path": "objects/docs/notes.txt", "isDir": False},
        {"path": "objects/docs", "isDir": True},
    ],
}

r = post(f"/deposits/{slug}/mets/delete", selection,
         extra_headers={"If-Match": deposit["metsETag"]})
pprint(r.json())

# What cannot be deleted, whatever you send: the objects folder, metadata/ad-hoc, a folder that
# still has files in it, and files in the root other than the BagIt ones. All 400 Bad Request.
