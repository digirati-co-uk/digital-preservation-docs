"""
Putting the deposit's files into its METS file.

Uploading a file to the workspace does not make it part of the object: the METS file says what the
object consists of, and synchronising the two is a separate, deliberate step. This is what you call
after uploading files, and again after running tools over them, to bring their metadata into METS.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, post, pprint

deposit = ensure_deposit()
slug = deposit_slug(deposit)

filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()
mets = get(f"/deposits/{slug}/parsed-mets").json()
in_mets = {file["localPath"] for file in mets["files"]}


def files_in(directory, found=None):
    found = found if found is not None else []
    for file in directory["files"]:
        found.append(file["localPath"])
    for child in directory["directories"]:
        files_in(child, found)
    return found


# Only paths in or below objects/ or metadata/ are added; files in the root are ignored. Parent
# folders are created for you, so there is no need to list them.
to_add = [path for path in files_in(filesystem)
          if path not in in_mets and path.startswith(("objects/", "metadata/"))]
print(f"Adding {len(to_add)} files to the METS")

# If-Match must carry the METS ETag exactly as the API gave it, quotation marks included. The
# deposit's metsETag is the same value as the ETag header of GET /deposits/{id}/mets.
r = post(f"/deposits/{slug}/mets", to_add, extra_headers={"If-Match": deposit["metsETag"]})
pprint(r.json())

# Submitting the same files again updates their entries - which is how tool output metadata
# produced after the first call gets into the METS.
