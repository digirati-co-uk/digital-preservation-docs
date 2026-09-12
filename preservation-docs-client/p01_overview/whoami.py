"""
The first call to make with new credentials: who does the API think I am?
"""
import sys

import settings
from preservation import get, pprint

problems = settings.check()
if problems:
    print("Configuration problems in .env:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)

# The `name` is what your actions will be recorded under (createdBy, preservedBy...).
# The `source` says where that name came from: the token, the X-Client-Identity header,
# or a signed-in user.
r = get("/whoami")
if r.status_code == 200:
    pprint(r.json())
else:
    print("No identity information from this instance; see the Authentication page.")
