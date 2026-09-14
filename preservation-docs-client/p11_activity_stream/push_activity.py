"""
Pushing an event onto the Activity Stream.

Use this when something a consumer derives from an Archival Group has changed, but the Archival
Group itself has not - a corrected catalogue record, say. The consumer needs no special handling:
the pushed event looks like any other Update.

Nothing is preserved by this. No new version is created.
"""
import settings
from preservation import get, post

# Find an Archival Group to nudge. Any existing one will do; here we take the most recent one
# the stream already knows about, which saves browsing the repository.
collection = get("/activity/archivalgroups/collection").json()
last_page = get(collection["last"]["id"]).json()

archival_group = None
for activity in reversed(last_page.get("orderedItems", [])):
    candidate = activity["object"]["id"]
    # The seeded first event in an empty stream points at example.com, not at this repository.
    if candidate.startswith(settings.PRESERVATION_API_HOST):
        archival_group = candidate
        break

if archival_group is None:
    print("No Archival Group found in the stream to push an event for")
    raise SystemExit

# The API validates all of this: type must be Update, object.type must be ArchivalGroup, and
# object.id must be an Archival Group on this API's own host. Anything else is a 400.
# Any startTime or endTime you send is ignored - the API stamps the event with the time of the POST.
response = post("/activity/archivalgroups/collection", {
    "type": "Update",
    "object": {
        "id": archival_group,
        "type": "ArchivalGroup",
    },
})
print(f"Pushed: {response.status_code} (204 means accepted)")

# It arrives at the end of the stream, as an Update with no seeAlso.
collection = get("/activity/archivalgroups/collection").json()
last_page = get(collection["last"]["id"]).json()
newest = last_page["orderedItems"][-1]
print(f"Newest activity is now: {newest['type']} {newest['object']['id']} at {newest['endTime']}")
