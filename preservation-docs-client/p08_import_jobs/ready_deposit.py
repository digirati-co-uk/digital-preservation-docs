"""
A deposit that is ready for an Import Job, for the samples on this page to work with.

Not a sample in its own right - import `ready_deposit()` from it. Three things have to be true
before the API will generate a diff:

  * the deposit has an `archivalGroup` - the API needs to know what to compare the files with,
    even when nothing exists there yet;
  * every file in the workspace is in the METS, with a SHA256 digest;
  * no Import Job has already run from this deposit.

The first two are what this helper arranges; the third is why the samples print the deposit id
and expect you to make a new deposit when you have preserved one.
"""
import os

import settings
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, patch, post


def archival_group_uri(name: str = "import-job-example") -> str:
    """Where in the repository the samples put their objects. The parent Container must exist -
    see p03_repository/create_and_delete_container.py."""
    name = os.environ.get("DOCS_ARCHIVAL_GROUP_NAME", name)
    return f"{settings.PRESERVATION_API_HOST}/repository/{settings.DOCS_CONTAINER_PATH}/{name}"


def files_in(directory, found=None):
    found = found if found is not None else []
    for file in directory["files"]:
        found.append(file["localPath"])
    for child in directory["directories"]:
        files_in(child, found)
    return found


def active_deposit_for(archival_group: str) -> dict | None:
    """The Deposit already working on this Archival Group, if there is one.

    Only one active Deposit may exist for an Archival Group at a time - creating or patching a
    second gets 409. So rather than making a deposit that cannot be used, reuse the one that is
    already there."""
    path = archival_group.split("/repository/", 1)[-1]
    page = get("/deposits", params={"archivalGroupPath": path}).json()
    return page["deposits"][0] if page["deposits"] else None


def ready_deposit() -> dict:
    archival_group = archival_group_uri()

    deposit = active_deposit_for(archival_group)
    if deposit and deposit.get("preserved"):
        # A Deposit is good for exactly one Import Job. Once it has preserved something, asking it
        # for another diff is a 409, so start a new one rather than reuse this.
        print(f"The deposit for {archival_group} has already been preserved; making a new one")
        deposit = None
    if deposit:
        print(f"Reusing the active deposit for {archival_group}")
    else:
        deposit = ensure_deposit()
        r = patch(f"/deposits/{deposit_slug(deposit)}", {
            "type": "Deposit",
            "archivalGroup": archival_group,
            "archivalGroupName": "An object made by the documentation samples",
        })
        if r.status_code != 200:
            raise SystemExit(
                f"Could not point the deposit at {archival_group}: {r.status_code} {r.text}")
        deposit = r.json()

    slug = deposit_slug(deposit)

    # Always fetch the deposit by id before using its metsETag. The listing does not carry one -
    # only GET /deposits/{id} populates it - and nor does the response to creating one.
    deposit = get(f"/deposits/{slug}").json()

    # Bring the METS into line with the workspace. Only paths in or below objects/ or metadata/
    # are added; anything in the deposit but not in the METS would fail the diff.
    filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()
    mets = get(f"/deposits/{slug}/parsed-mets").json()
    in_mets = {file["localPath"] for file in mets["files"]}
    to_add = [path for path in files_in(filesystem)
              if path not in in_mets and path.startswith(("objects/", "metadata/"))]
    if to_add:
        print(f"Adding {len(to_add)} file(s) to the METS first")
        post(f"/deposits/{slug}/mets", to_add, extra_headers={"If-Match": deposit["metsETag"]})

    # Re-fetch: the METS edit changed the deposit's metsETag.
    return get(f"/deposits/{slug}").json()
