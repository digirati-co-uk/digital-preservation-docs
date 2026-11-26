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

# An example rule, for an installation (like Leeds) that derives an Access Tier, type "tier".
# None means "publish with no roles"; NOT_PUBLISHED means "leave the file out".
NOT_PUBLISHED = "not published"
ROLES_BY_TIER = {
    "0": None,
    "1": None,
    "2": "https://api.example/customers/7/roles/clickthrough",
    "3": "https://api.example/customers/7/roles/staff",
    "4": NOT_PUBLISHED,
    "5": NOT_PUBLISHED,
}
PRESERVATION_PREFIX = "Preservation: "


def find_first_archival_group(container):
    for child in container.get("containers", []):
        if child["type"] == "ArchivalGroup":
            return child
        found = find_first_archival_group(get(child["id"]).json())
        if found:
            return found
    return None


def condition(resource, condition_type):
    """The value of one access condition on a canvas, range or manifest, or None."""
    for entry in resource.get("accessConditions", []):
        if entry["type"] == condition_type:
            return entry["value"]
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

# --- 3. Access: roles per asset, from each canvas's resolved conditions ------------------------

canvases = {canvas["id"]: canvas for canvas in manifest["items"]}
published = []
for painted in manifest.get("paintedResources", []):
    canvas = canvases[painted["canvasPainting"]["canvasId"]]
    tier = condition(canvas, "tier")
    role = ROLES_BY_TIER.get(tier) if tier is not None else None
    print(f"  {painted['asset']['id'][-50:]:<50} tier={tier}  ->  {role or 'open'}")
    if role == NOT_PUBLISHED:
        canvases.pop(canvas["id"])
        continue
    if role:
        painted["asset"]["roles"] = [role]
    published.append(painted)

# Leaving a file out means leaving out its canvas too, and renumbering what remains.
manifest["items"] = [c for c in manifest["items"] if c["id"] in canvases]
for order, painted in enumerate(published):
    painted["canvasPainting"]["canvasOrder"] = order
manifest["paintedResources"] = published

# --- 4. What would be sent, and what would be deleted ------------------------------------------

# formerAssets is for the builder, not for IIIF Cloud Services: take it out before sending.
former = manifest.pop("formerAssets", [])
out = Path(tempfile.gettempdir()) / "w10-iiif-cs-manifest.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"\nWould PUT {len(manifest['items'])} canvases: {out}")

for asset in former:
    print(f"Would DELETE asset {asset['id']} (last in {asset['lastVersion']}), if we registered it")
if not former:
    print("No former assets to delete")
