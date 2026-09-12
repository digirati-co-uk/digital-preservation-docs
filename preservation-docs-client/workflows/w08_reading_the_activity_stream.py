"""
Following the Activity Stream.

End to end: a consumer that keeps up with everything the platform preserves. It implements the IIIF
Change Discovery processing algorithm - read backwards from the last page until you reach something
you have seen before, then act on what you collected, oldest first.

Position is remembered in a small JSON file next to this script. A real consumer would keep it
wherever it keeps its state; what matters is that it records the last activity it PROCESSED, not a
page number. Pages are numbered by position from the start of the stream, so page 7 means something
different once seven more objects have been preserved.

  python -m workflows.w08_reading_the_activity_stream
"""
import json
import os
from pathlib import Path

import settings
from preservation import get

STATE_FILE = Path(os.environ.get("DOCS_ACTIVITY_STATE", "workflows/.activity-position.json"))


def load_position():
    """The last activity we processed: its object id and endTime."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


def save_position(activity):
    STATE_FILE.write_text(json.dumps({
        "id": activity["object"]["id"],
        "endTime": activity["endTime"],
    }, indent=2))


def already_seen(activity, position):
    if position is None:
        return False
    # endTime is the ordering key: anything at or before where we got to is done with.
    return activity["endTime"] <= position["endTime"]


def page_number(page_uri):
    return int(page_uri.rstrip("/").rsplit("/", 1)[-1])


position = load_position()
print(f"Last processed: {position}")

collection = get("/activity/archivalgroups/collection").json()
print(f"\n{collection['totalItems']} activities, first {collection['first']['id']}, "
      f"last {collection['last']['id']}")

# Walk backwards from the last page, collecting what we have not processed, until we recognise
# something. Going backwards means we read as few pages as it takes to catch up, however long we
# were away - which is the whole point of the algorithm.
new_activities = []
page_uri = collection["last"]["id"]
caught_up = False

while page_uri and not caught_up:
    page = get(page_uri).json()
    print(f"Page {page_number(page['id'])}: {len(page.get('orderedItems') or [])} activities")
    for activity in reversed(page.get("orderedItems") or []):
        if already_seen(activity, position):
            caught_up = True
            break
        new_activities.append(activity)
    page_uri = page.get("prev", {}).get("id") if page.get("prev") else None

new_activities.reverse()   # oldest first, which is the order to act in
print(f"\n{len(new_activities)} activity/activities to process")

# An object preserved four times while we were down produces four activities. If the work is
# "rebuild whatever we derive from this object", once is enough - so collapse the batch by object,
# keeping the latest. Only safe within one catch-up batch, and only if the work is idempotent.
latest_per_object = {}
for activity in new_activities:
    latest_per_object[activity["object"]["id"]] = activity

for object_id, activity in latest_per_object.items():
    # Objects you do not recognise can appear - the stream's first entry is a placeholder from
    # when the database was created. Skip them rather than failing on them.
    if not object_id.startswith(f"{settings.PRESERVATION_API_HOST}/repository/"):
        print(f"\nSkipping {object_id}: not an object in this repository")
        continue

    # `type` is Create for a first version and Update for every one after it. Note the capitals.
    print(f"\n{activity['type']} {object_id} at {activity['endTime']}")

    # `seeAlso` names the Import Job Result that produced the version, but as a Storage API URI,
    # which a Preservation API client cannot dereference. It is an opaque identifier: useful for
    # recognising two activities that came from the same import, not something to fetch.
    for see_also in activity["object"].get("seeAlso") or []:
        print(f"  from import {see_also['id']}")

    # This is where a real consumer does its work - load the object, or its METS:
    #   archival_group = get(object_id).json()
    #   mets = get(object_id, params={"view": "mets"}).content

if new_activities:
    save_position(new_activities[-1])
    print(f"\nPosition saved: {new_activities[-1]['endTime']}")
else:
    print("\nNothing new. The stream lags by up to a minute or so behind a preserved version,")
    print("and a suppressed event never appears at all.")
