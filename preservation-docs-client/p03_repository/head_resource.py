"""
HEAD tells you cheaply whether a resource exists and what type it is, without the body.
Run with a repository path as the argument, e.g.  python head_resource.py library/manuscripts/ms-342
"""
import sys

from preservation import head

path = sys.argv[1] if len(sys.argv) > 1 else ""

r = head(f"/repository/{path}")
if r.status_code == 200:
    print(f"Exists; type is {r.headers.get('X-Preservation-Resource-Type')}")
elif r.status_code == 410:
    print("Gone: a resource used to exist here and was deleted (a tombstone)")
elif r.status_code == 404:
    print("Not found")

# Something that certainly does not exist
head("/repository/no-such-container-abc123")
