"""
Creating a deposit: the workspace you assemble files in before preserving them.

The API answers with the Deposit, whose `files` property is the S3 prefix that belongs to it.
Everything you upload for this object goes in or below `objects/` under that prefix.
"""
import sys

import settings
from preservation import post, pprint

problems = settings.check()
if problems:
    print("Configuration problems in .env:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)

# Every property here is optional. `template` decides the shape of the workspace and whether the
# platform manages a METS file for you: None (you supply everything), RootLevel, or BagIt.
# `archivalGroup` is where this will end up in the repository - you can set it later instead.
r = post("/deposits", {
    "type": "Deposit",
    "template": "RootLevel",
    "archivalGroupName": "A deposit made by the documentation samples",
    "submissionText": "Created while reading the Deposits page",
})

print(f"Location: {r.headers.get('Location')}")
deposit = r.json()
pprint(deposit)

# The three properties you will use next:
print(f"\nWorkspace:  {deposit['files']}")        # upload files here, with the S3 API
print(f"Status:     {deposit['status']}")         # "new" - ready to work on
print(f"METS ETag:  {deposit['metsETag']}")       # send this as If-Match when editing the METS
