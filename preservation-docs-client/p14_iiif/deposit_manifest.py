"""
A Deposit as a IIIF Manifest.

GET /deposits/{id}/iiif is authenticated and answers with a redirect to a tokenised URL. That
tokenised URL needs no Authorization header, which is what lets you hand it to a viewer running
in a browser. Treat the token as a secret: it opens the deposit's files.

Requires the instance to have EnableIiifMediaEndpoints switched on. With the flag off the
redirect still happens but the tokenised URL answers 401.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get

deposit = ensure_deposit()
slug = deposit_slug(deposit)

# requests follows the 302 for us, so r.url is the tokenised URL we ended up at.
response = get(f"/deposits/{slug}/iiif")
manifest = response.json()
token_url = response.url
print(f"Manifest URL: {token_url}")

# The manifest's metadata block summarises the deposit itself.
for pair in manifest.get("metadata", []):
    label = next(iter(pair["label"].values()))[0]
    value = next(iter(pair["value"].values()))[0]
    print(f"  {label}: {value}")

print(f"\n{len(manifest.get('items', []))} canvases")
for canvas in manifest.get("items", [])[:5]:
    # Every canvas is a placeholder: a grey image is painted on it, and the file itself, whatever
    # kind it is, is reached through the canvas's rendering link.
    original = canvas["rendering"][0]
    print(f"  {original.get('format', '-'):<28} {original['id']}")

# Ranges come from the METS logical structMaps. Type, Name and id in a Range's metadata are how
# it is matched back to the structMap division it came from - keep them.
for range_ in manifest.get("structures", []):
    label = next(iter(range_["label"].values()))[0]
    print(f"\nRange: {label} ({len(range_.get('items', []))} items)")
