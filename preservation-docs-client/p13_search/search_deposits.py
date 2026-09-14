"""
Search. One request, two independently paged result sets, plus an identifier lookup.

Note the paging parameter is `pageNumber`, counting from 0 - not `page` counting from 1, which
is what /deposits uses. An unrecognised parameter is ignored rather than rejected, so getting
this wrong silently gives you page 0.
"""
from preservation import get

TERM = "objects"

results = get("/search", params={"text": TERM, "pageNumber": 0, "pageSize": 10}).json()

# Both result sets can be null rather than an empty page object, so check before reading them.
deposit_search = results.get("depositSearch")
if deposit_search:
    print(f"{deposit_search['total']} matching deposits "
          f"(page {deposit_search['page']} of {deposit_search['pageSize']}):")
    for deposit in deposit_search["deposits"]:
        # These are complete Deposit resources, the same as GET /deposits/{id} returns.
        print(f"  {deposit['id']}  {deposit['status']:>9}  "
              f"{deposit.get('archivalGroupName') or '(no name)'}")
else:
    print("No matching deposits")

file_search = results.get("fedoraSearch")
if file_search:
    print(f"\n{file_search['total']} matching preserved files, {file_search['count']} on this page:")
    for row in file_search["results"]:
        # fedoraId is the internal identifier; the part after info:fedora/ is the path
        # under /repository, so the API URI can be rebuilt from it.
        path = row["fedoraId"].removeprefix("info:fedora/")
        print(f"  {row['mimeType']:<20} {row['contentSize']:>10}  /repository/{path}")
else:
    print("\nNo matching preserved files")

# The search term is NOT echoed back: `text` and `searchType` are always null. Keep your own copy.
print(f"\ntext in response: {results.get('text')}  (always null - we searched for {TERM!r})")

# If the term looks like a known identifier, the record comes back too. Institution-specific:
# an instance with no identity service always returns null here.
identifier = results.get("identifier")
if identifier:
    print(f"Identifier match: {identifier.get('title')} -> {identifier.get('repositoryUri')}")

# Paging one result set without disturbing the other: `type` names the set that `pageNumber`
# applies to, and `otherPage` holds the other one where it was. Both are always searched.
next_page = get("/search", params={
    "text": TERM,
    "type": "Deposits",
    "pageNumber": 1,    # second page of deposits
    "otherPage": 0,     # first page of files, unchanged
    "pageSize": 10,
}).json()
if next_page.get("depositSearch"):
    print(f"\nDeposits page {next_page['depositSearch']['page']}: "
          f"{len(next_page['depositSearch']['deposits'])} results")
