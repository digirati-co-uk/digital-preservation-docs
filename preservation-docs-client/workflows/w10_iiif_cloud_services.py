"""
IIIF from preserved objects: what a builder does with the IIIF Cloud Services projection.

A DRY RUN. It fetches an Archival Group's ?view=iiif-cs Manifest, applies an example access rule
and some placeholder decoration, then writes what it would submit to IIIF Cloud Services to a file in
the temp folder, and lists the assets it would delete. It never calls IIIF Cloud Services: a real
builder sends the decorated Manifest with PUT /{customer}/manifests/{id} and the header
X-IIIF-CS-Show-Extras: All, then deletes the former assets it registered.

    python -m workflows.w10_iiif_cloud_services                   # the first Archival Group found
    python -m workflows.w10_iiif_cloud_services library/ms-342    # a particular one

The role URIs and the tier rule are EXAMPLES. Which roles exist, and what each access condition
means on the web, are the institution's decisions, configured in IIIF Cloud Services.
"""
import json
import sys
import tempfile
from pathlib import Path

from preservation import get

# An example rule: what each placeholder role the platform puts on an asset means here. On Leeds
# instances (Iiif:RoleConditionTypes = tier) every asset has exactly one token, its tier.
# OPEN means "remove the token: no roles"; NOT_PUBLISHED means "leave the file out".
OPEN = "open"
NOT_PUBLISHED = "not published"
ROLE_FOR_TOKEN = {
    "urn:x-access-condition:tier:0": OPEN,
    "urn:x-access-condition:tier:1": OPEN,
    "urn:x-access-condition:tier:2": "https://api.example/customers/7/roles/clickthrough",
    "urn:x-access-condition:tier:3": "https://api.example/customers/7/roles/staff",
    "urn:x-access-condition:tier:4": NOT_PUBLISHED,
    "urn:x-access-condition:tier:5": NOT_PUBLISHED,
}


def real_roles(tokens):
    """The asset's roles with every token mapped, or NOT_PUBLISHED. An unmapped token is an error:
    the platform's tokens exist so that a gap in this table fails rather than publishing openly."""
    roles = []
    for token in tokens:
        if token not in ROLE_FOR_TOKEN:
            raise SystemExit(f"No rule for {token}: add it to ROLE_FOR_TOKEN")
        role = ROLE_FOR_TOKEN[token]
        if role == NOT_PUBLISHED:
            return NOT_PUBLISHED
        if role != OPEN:
            roles.append(role)
    return roles
PRESERVATION_PREFIX = "Preservation: "


def find_first_archival_group(container):
    for child in container.get("containers", []):
        if child["type"] == "ArchivalGroup":
            return child
        found = find_first_archival_group(get(child["id"]).json())
        if found:
            return found
    return None


def label_of(pair):
    return next(iter(pair["label"].values()))[0]


# --- 1. Which Archival Group, and its IIIF-CS projection ---------------------------------------

if len(sys.argv) > 1:
    group = get(f"/repository/{sys.argv[1]}?view=lightweight").json()
else:
    group = find_first_archival_group(get("/repository").json())
    if group is None:
        print("No Archival Groups in the repository")
        raise SystemExit

# A lightweight Archival Group links to both projections; a full one does too.
iiif_cs = group.get("iiifCs") or get(f"{group['id']}?view=lightweight").json()["iiifCs"]
manifest = get(iiif_cs).json()
print(f"{label_of({'label': manifest['label']})}: {len(manifest['items'])} canvases, "
      f"{len(manifest.get('paintedResources', []))} painted resources, "
      f"{len(manifest.get('formerAssets', []))} former assets")

# --- 2. Decorate: what only the catalogue knows ------------------------------------------------

record_ids = [p for p in manifest.get("metadata", []) if label_of(p).startswith(PRESERVATION_PREFIX + "Record identifier")]
print("Look these up in the catalogue:", [next(iter(p["value"].values()))[0] for p in record_ids])
manifest["summary"] = {"en": ["(from the catalogue)"]}
manifest["slug"] = group["id"].rstrip("/").split("/")[-1]
manifest["parent"] = "https://presentation-api.example/7/collections/example"

# Our metadata labels all start "Preservation: ". Keep the format and size, drop the rest.
keep = {PRESERVATION_PREFIX + "Format", PRESERVATION_PREFIX + "Size"}
for canvas in manifest["items"]:
    canvas["metadata"] = [p for p in canvas.get("metadata", []) if label_of(p) in keep]

# --- 3. Access: replace each asset's placeholder roles with real ones -------------------------

canvases = {canvas["id"]: canvas for canvas in manifest["items"]}
published = []
for painted in manifest.get("paintedResources", []):
    asset = painted["asset"]
    roles = real_roles(asset.get("roles", []))
    print(f"  {asset['id'][-50:]:<50} {asset.get('roles')}  ->  {roles or 'open'}")
    if roles == NOT_PUBLISHED:
        canvases.pop(painted["canvasPainting"]["canvasId"])
        continue
    if roles:
        asset["roles"] = roles
    else:
        asset.pop("roles", None)
    asset.pop("accessConditions", None)   # the builder's, not IIIF Cloud Services'
    # Content new or changed in this version: ask IIIF Cloud Services to ingest it again
    # (needed until dlcs/iiif-presentation#727 passes a changed origin on by itself).
    if asset.pop("contentVersion", None) == manifest.get("objectVersion"):
        painted["reingest"] = True
    for adjunct in asset.get("adjuncts", []):
        # IIIF Cloud Services gives an adjunct its asset's access; say so where that isn't what METS says.
        if adjunct.get("accessDiffersFromAsset"):
            print(f"      adjunct {adjunct['id'][-40:]} has its own access conditions: {adjunct.get('accessConditions')}")
        adjunct.pop("roles", None)
        adjunct.pop("accessConditions", None)
        adjunct.pop("accessDiffersFromAsset", None)
        adjunct.pop("contentVersion", None)
    published.append(painted)

# Leaving a file out means leaving out its canvas too, and renumbering what remains.
manifest["items"] = [c for c in manifest["items"] if c["id"] in canvases]
for order, painted in enumerate(published):
    painted["canvasPainting"]["canvasOrder"] = order
manifest["paintedResources"] = published

# --- 4. What would be sent, and what would be deleted ------------------------------------------

# formerAssets is for the builder, not for IIIF Cloud Services: take it out before sending.
former = manifest.pop("formerAssets", [])
manifest.pop("objectVersion", None)
out = Path(tempfile.gettempdir()) / "w10-iiif-cs-manifest.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"\nWould PUT {len(manifest['items'])} canvases: {out}")

for asset in former:
    print(f"Would DELETE asset {asset['id']} (last in {asset['lastVersion']}), if we registered it")
if not former:
    print("No former assets to delete")
