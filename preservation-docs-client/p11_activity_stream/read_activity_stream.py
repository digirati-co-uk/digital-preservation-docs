"""
Reading the Activity Stream backwards to a watermark.

The stream is oldest-first within a page, and pages run oldest to newest. To catch up you start
at the NEWEST page, walk its items backwards, and stop as soon as you meet an endTime you have
already processed. Then you process what you gathered oldest-first, advancing the watermark as
each one succeeds - so a failure part way through does not skip the rest.

A real consumer stores the watermark somewhere durable. This one just picks a date.
"""
from datetime import datetime, timedelta, timezone

from preservation import get

# The high-water mark: the endTime of the last activity we successfully processed. A consumer
# running for the first time uses a date far enough back to cover everything it cares about.
watermark = datetime.now(timezone.utc) - timedelta(days=7)
print(f"Catching up on everything since {watermark.isoformat()}")

collection = get("/activity/archivalgroups/collection").json()
print(f"{collection['totalItems']} activities in the stream")

# Follow the links; never build page URIs yourself. Page numbers shift as the stream grows.
page_uri = collection["last"]["id"]
new_activities = []
reached_watermark = False

while page_uri and not reached_watermark:
    page = get(page_uri).json()
    # reversed(): the page is oldest-first, and we are reading backwards in time.
    for activity in reversed(page.get("orderedItems", [])):
        end_time = datetime.fromisoformat(activity["endTime"])
        if end_time <= watermark:
            reached_watermark = True
            break
        new_activities.append(activity)
    # "prev" is the next page BACK in time. Absent on page 1, which ends the walk.
    page_uri = page.get("prev", {}).get("id")

print(f"\n{len(new_activities)} new activities")

# Process oldest-first, which is the order they happened in.
for activity in reversed(new_activities):
    archival_group = activity["object"]["id"]
    print(f"  {activity['endTime']}  {activity['type']:<6}  {archival_group}")

    # seeAlso is a list, and its entries are Storage API URIs that most callers cannot fetch.
    # Act on object.id; treat seeAlso as an opaque marker of which import job caused this.
    for see_also in activity["object"].get("seeAlso", []):
        print(f"      caused by {see_also['type']} {see_also['id']}")

    # Whatever this consumer does with a changed Archival Group would go here - and only after
    # it has succeeded would the watermark move on:
    watermark = datetime.fromisoformat(activity["endTime"])

print(f"\nNew watermark: {watermark.isoformat()}")
