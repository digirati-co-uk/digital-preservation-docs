"""
Browse the repository from its root, following `id` links down through Containers until
an Archival Group is found, then fetch that Archival Group in full.
"""
from preservation import get, pprint


def find_first_archival_group(container: dict) -> dict | None:
    """Depth-first walk of the `containers` lists until a child of type ArchivalGroup turns up."""
    for child in container.get("containers", []):
        if child["type"] == "ArchivalGroup":
            return child
        # A child Container only carries its immediate children, so fetch it to look inside.
        found = find_first_archival_group(get(child["id"]).json())
        if found:
            return found
    return None


# The root is itself a Container, with the special type RepositoryRoot.
root = get("/repository").json()
print(f"Root type: {root['type']}, {len(root['containers'])} top-level containers")

ag_summary = find_first_archival_group(root)
if ag_summary is None:
    print("No Archival Groups found in the repository")
else:
    # An Archival Group response includes ALL its descendant containers and binaries.
    ag = get(ag_summary["id"]).json()
    print(f"Archival Group {ag['name']} at version {ag['version']['ocflVersion']}")
    pprint(ag)
