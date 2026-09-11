"""
Containers outside Archival Groups organise the repository. They are the only kind of
repository resource you create directly; everything inside an Archival Group arrives
through an Import Job.
"""
import settings
from preservation import get, put, delete, head

path = f"/repository/{settings.DOCS_CONTAINER_PATH}/docs-temp-container"

# PUT with a body giving the display name...
r = put(path, {"type": "Container", "name": "A temporary container made by the docs samples"})
print(f"Created: {r.status_code}, Location: {r.headers.get('Location')}")

# ...or with no body at all, in which case the name is taken from the path.
# put(path)

container = get(path).json()
print(f"{container['type']} {container['name']} has {len(container['containers'])} containers "
      f"and {len(container['binaries'])} binaries")

# DELETE without purge leaves a tombstone: the path answers 410 and cannot be reused.
delete(path)
head(path)

# DELETE again with purge removes it completely: the path answers 404 and can be reused.
delete(path + "?purge=true")
head(path)
