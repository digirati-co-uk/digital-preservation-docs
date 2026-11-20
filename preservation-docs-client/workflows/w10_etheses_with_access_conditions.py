"""
An e-thesis with access conditions.

The same deposit as w09_etheses.py, with one more step before it is preserved: the script says
who may see the thesis, and on what terms. Here the whole thesis is given one access restriction
and a statement of rights, and its research data folder a stricter restriction of its own.

  python -m workflows.w10_etheses_with_access_conditions

Add --review to leave a person to preserve the deposit in the UI.

A script doesn't have to do this. It can stop after describing the files (w09 with --review),
and a person then sets the access conditions in the UI before preserving.

The values come from the installation's own vocabulary, GET /access-conditions. So that this
sample runs anywhere, it takes the first and last restriction it is offered; a real script
chooses the ones that are true of the thesis. Set DOCS_ARCHIVAL_GROUP_NAME (default
"my-thesis-with-access-conditions") for which thesis this run works on.
"""
import os

import settings
from preservation import get, post, pprint
from workflows.w09_etheses import container, describe, finish, new_thesis_deposit, slug_of

name = os.environ.get("DOCS_ARCHIVAL_GROUP_NAME", "my-thesis-with-access-conditions")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{container}/{name}"


def set_access(deposit, change):
    """Set the access conditions of one file or folder. Everything beneath a folder inherits them."""
    slug = slug_of(deposit)
    # Each change to the METS needs its current ETag, and each change gives it a new one.
    mets_etag = get(f"/deposits/{slug}").json()["metsETag"]
    r = post(f"/deposits/{slug}/mets/access", change, extra_headers={"If-Match": mets_etag})
    if r.status_code != 204:
        # A 400 names the value that was not accepted, and lists the choices.
        pprint(r.json())
        raise SystemExit(f"Access conditions not set: {r.status_code}")


# The thesis files and the sidecar, described by the pipeline: exactly as in w09.
deposit = new_thesis_deposit(archival_group)
describe(deposit)

# What this installation lets you say.
profile = get("/access-conditions").json()
restrictions = [restriction["value"] for restriction in profile["restrictionAxis"]["values"]]
print(f"\nAccess restrictions here: {restrictions}")

# The whole thesis: a restriction, and a statement of rights. An installation either has its own
# statements, from which the platform works out the rights statement, or takes a rights statement
# directly.
whole_thesis = {"path": "objects", "accessRestrictions": [restrictions[0]]}
if profile.get("statements"):
    statements = [statement["value"] for statement in profile["statements"]["values"]]
    print(f"{profile['statements']['label']}s here: {statements}")
    whole_thesis["accessStatement"] = statements[0]
else:
    whole_thesis["rightsStatement"] = "http://rightsstatements.org/vocab/InC/1.0/"
set_access(deposit, whole_thesis)

# The research data: a stricter restriction. Nothing else is sent, so it keeps the statement of
# rights it inherits from objects.
set_access(deposit, {"path": "objects/data", "accessRestrictions": [restrictions[-1]]})

# What the METS now says about each. A file with nothing of its own inherits from its folder.
mets = get(f"/deposits/{slug_of(deposit)}/parsed-mets").json()
objects = next(d for d in mets["physicalStructure"]["directories"] if d["localPath"] == "objects")
data = next(d for d in objects["directories"] if d["localPath"] == "objects/data")
for directory in (objects, data):
    print(f"  {directory['localPath']}: {directory.get('accessRestrictions')}")

finish(deposit)
