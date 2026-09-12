"""
An Archival Group's versions, and the Storage Map that says where each version's files really are.

The Archival Group tells you WHAT is in each version. The Storage Map tells you WHERE the bytes
of a given version live in the OCFL object, which is the only way to reach the files of a version
that is no longer the head.
"""
from preservation import get, pprint


def find_first_archival_group(container):
    """Depth-first walk of the repository until an ArchivalGroup turns up."""
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

archival_group = get(summary["id"]).json()
path_under_root = archival_group["id"].split("/repository/", 1)[1]

# "version" is the one being shown; "versions" is all of them, oldest first.
print(f"{archival_group['name']} is at {archival_group['version']['ocflVersion']}")
for version in archival_group["versions"]:
    print(f"  {version['ocflVersion']:>4}  {version['mementoDateTime']}  ({version['mementoTimestamp']})")

# Metadata for an older version. The version parameter is only allowed with view=lightweight,
# so this tells you the resource existed then, but not what was in it.
first = archival_group["versions"][0]["ocflVersion"]
get(archival_group["id"], params={"view": "lightweight", "version": first})

# For the files of a version, ask for its storage map. The version parameter here takes either
# the OCFL label or the Memento timestamp; omit it for the head version.
storage_map = get(f"/ocfl/storagemap/{path_under_root}", params={"version": first}).json()
print(f"\nStorage map at {storage_map['version']['ocflVersion']} "
      f"(head is {storage_map['headVersion']['ocflVersion']}), "
      f"{storage_map['storageType']} bucket {storage_map['root']}")

for logical_path, origin_file in storage_map["files"].items():
    # fullPath names the version in which these bytes were FIRST written, which is often an
    # earlier version than the one asked for: OCFL does not copy unchanged files forward.
    location = f"{storage_map['root']}/{storage_map['objectPath']}/{origin_file['fullPath']}"
    print(f"  {logical_path}")
    print(f"      {origin_file['hash'][:12]}...  {location}")

# hashes is the reverse lookup: content digest -> path in storage. Two logical files with
# identical content share one entry, because OCFL stores those bytes once.
print(f"\n{len(storage_map['files'])} files, {len(storage_map['hashes'])} distinct contents")

# The same map is on the Archival Group itself, for the version you are looking at.
pprint(archival_group["storageMap"]["version"])
