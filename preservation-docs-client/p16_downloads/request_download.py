"""
Download a preserved file: request it, wait for its copy, take a link, fetch it.

  python -m p16_downloads.request_download

Set DOCS_FILE_PATH to the path under /repository of the file to download. By default it is a file
that the w02 workflow sample preserved.
"""
import hashlib
import os

import requests

import settings
from preservation import delete, get, post, pprint, wait_for_value

path = os.environ.get("DOCS_FILE_PATH", f"{settings.DOCS_CONTAINER_PATH}/w02-first-time/objects/about.txt")

# ---------------------------------------------------------------------------
# 1. Ask for the file. A 403 here means your caller may not download; a 404 that there is no
#    file at that path. The copy is being made when this returns.
# ---------------------------------------------------------------------------
r = post("/downloads", {"path": path, "reason": "Trying the downloads sample"})
if r.status_code != 200:
    pprint(r.json())
    raise SystemExit(f"Download not accepted: {r.status_code}")
download = r.json()
pprint(download)

# ---------------------------------------------------------------------------
# 2. Wait until the copy is ready. Usually a second or two.
# ---------------------------------------------------------------------------
download = wait_for_value(f"/downloads/{download['id']}", "status", "ready", interval=2, retries=30)
if download is None:
    raise SystemExit("The copy is not ready.")

# ---------------------------------------------------------------------------
# 3. Take a link. It works for a couple of minutes, and needs no credentials: anyone holding it
#    can fetch the file, so ask for one when you are about to use it. Ask again for another.
# ---------------------------------------------------------------------------
link = post(f"/downloads/{download['id']}/link").json()
print(f"\nThe link expires at {link['expires']}")

# ---------------------------------------------------------------------------
# 4. Fetch the file, and check it is the file that was preserved.
# ---------------------------------------------------------------------------
content = requests.get(link["url"]).content
digest = hashlib.sha256(content).hexdigest()
print(f"Fetched {len(content)} bytes of {download['name']}")
print(f"sha256 {digest} - {'matches' if digest == download['digest'] else 'DOES NOT MATCH'} the preserved file")

# ---------------------------------------------------------------------------
# 5. Remove the copy now that it has been fetched. It would otherwise stay until it expires. The
#    record of the request stays either way.
# ---------------------------------------------------------------------------
delete(f"/downloads/{download['id']}")
pprint(get(f"/downloads/{download['id']}").json())
