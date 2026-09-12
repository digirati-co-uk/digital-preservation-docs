"""
Obtain an access token with the OAuth2 client-credentials grant, look at what is in it, and
check what the API makes of it.

The token is a JWT: three base64url segments separated by dots. We decode the middle one purely
to show what the API sees - a client never needs to do this, and never validates it itself.
"""
import base64
import json
import sys

import settings
from preservation import get, get_access_token, pprint

problems = settings.check()
if problems:
    print("Configuration problems in .env:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)

if settings.DISABLE_AUTH:
    print("DISABLE_AUTH is true, so there is no token to fetch; calling /whoami anyway.")
else:
    print(f"Requesting a token from {settings.TOKEN_ENDPOINT}")
    print(f"  client_id: {settings.CLIENT_ID}")
    print(f"  scope:     {settings.SCOPE}")
    token = get_access_token()

    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)  # base64url segments arrive without padding
    claims = json.loads(base64.urlsafe_b64decode(payload))

    print("\nClaims in the token:")
    # aud  - who the token is for; must match an audience this API validates
    # azp  - the application that asked for it (or `appid` in older token formats); this is what
    #        the API looks up in its allow-list of known clients
    # exp  - expiry, as a Unix timestamp; request a new token shortly before this
    for claim in ["aud", "iss", "azp", "appid", "roles", "scp", "exp"]:
        if claim in claims:
            print(f"  {claim}: {claims[claim]}")

# `source` says how the API resolved the name: "token" if it recognised the app id above,
# "header-fallback" if it fell back to the X-Client-Identity header we sent.
r = get("/whoami")
pprint(r.json())
