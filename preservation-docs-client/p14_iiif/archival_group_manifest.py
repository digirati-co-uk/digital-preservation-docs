"""
An Archival Group as a IIIF Manifest.

GET /iiif/{path}, where {path} is the Archival Group's path under /repository. Authenticated like
the rest of the API; there is no tokenised variant. The path must resolve to an Archival Group
exactly, and that Archival Group must contain a METS file - anything else is a 404.

The painting annotations point at the Binaries' /repository/... URIs, which return JSON rather
than image bytes, so this manifest is useful for its structure but a viewer cannot display it.
"""
from preservation import get


def find_first_archival_group(container):
    for child in container.get("containers", []):
        if child["type"] == "ArchivalGroup":
            return child
        found = find_first_archival_group(get(child["id"]).json())
        if found:
            return found
    return None


summary = find_first_archival_group(get("/repository").json())
if summary is None:
    print("No Archival Groups in the repository")
    raise SystemExit

path_under_root = summary["id"].split("/repository/", 1)[1]
manifest = get(f"/iiif/{path_under_root}").json()

label = next(iter(manifest["label"].values()))[0]
print(f"{label}: {len(manifest.get('items', []))} canvases")

for canvas in manifest.get("items", []):
    canvas_label = next(iter(canvas["label"].values()))[0]
    size = ""
    if canvas.get("width"):
        size = f"{canvas['width']}x{canvas['height']}"
    if canvas.get("duration"):
        size = f"{size} {canvas['duration']}s".strip()
    print(f"  {canvas_label:<50} {size}")

    # Supplementing annotations are the METS file links - a transcript, an OCR file and so on.
    # Their targets do not get canvases of their own.
    for page in canvas.get("annotations", []):
        for annotation in page["items"]:
            provides = annotation.get("provides", ["-"])[0]
            print(f"      supplements with: {provides}")


def show_ranges(ranges, depth=1):
    """Ranges come from the METS logical structMaps and nest as deeply as the METS does."""
    for range_ in ranges:
        label = next(iter(range_["label"].values()))[0]
        print("  " * depth + f"Range: {label}")
        children = [item for item in range_.get("items", []) if item["type"] == "Range"]
        canvases = [item for item in range_.get("items", []) if item["type"] != "Range"]
        if canvases:
            print("  " * (depth + 1) + f"{len(canvases)} canvases")
        show_ranges(children, depth + 1)


show_ranges(manifest.get("structures", []))
