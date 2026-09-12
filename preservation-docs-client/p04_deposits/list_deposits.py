"""
Listing deposits. The response is a page object - deposits, page, pageSize, total - not a list.

With no query parameters you get active deposits, newest first. Every other question is a
matter of narrowing that.
"""
from preservation import get

page = get("/deposits").json()
print(f"{page['total']} active deposits; showing page {page['page']} of {page['pageSize']}")
for deposit in page["deposits"][:5]:
    print(f"  {deposit['id']}  {deposit['status']:>9}  {deposit['created'][:10]}  "
          f"{deposit.get('archivalGroupName') or '(no name)'}")

# Narrowing. Dates are ISO 8601; agents can be given as a full URI or just the name part.
print("\nPreserved deposits, oldest first:")
page = get("/deposits", params={
    "status": "preserved",
    "orderBy": "preserved",
    "ascending": "true",
    "pageSize": 5,
}).json()
for deposit in page["deposits"]:
    print(f"  {deposit['preserved'][:10]}  {deposit['versionPreserved']:>4}  {deposit['preservedBy']}")

# To walk everything there has ever been: ShowAll for the active/inactive axis, ascending order
# so that deposits created while you page cannot shift a later page underneath you. Archived is
# a filter rather than an include, so leave it out to see archived and unarchived alike.
page = get("/deposits", params={
    "showAll": "true",
    "orderBy": "created",
    "ascending": "true",
    "page": 1,
    "pageSize": 100,
}).json()
print(f"\n{page['total']} deposits in total")
