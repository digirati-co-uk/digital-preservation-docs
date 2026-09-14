"""
A Deposit as a IIIF Manifest, and posting one back to change its logical structure.

GET /deposits/{id}/iiif is authenticated and answers with a redirect to a tokenised URL. That
tokenised URL needs no Authorization header, which is what lets you hand it to a viewer or a
manifest editor running in a browser. Treat the token as a secret: it opens the deposit's files.

Requires the instance to have EnableIiifMediaEndpoints switched on. With the flag off the
redirect still happens but the tokenised URL answers 401.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get, post

deposit = ensure_deposit()
slug = deposit_slug(deposit)

# requests follows the 302 for us, so r.url is the tokenised URL we ended up at.
response = get(f"/deposits/{slug}/iiif")
manifest = response.json()
token_url = response.url
print(f"Manifest URL: {token_url}")

# The same URL, given in a header so that an editor can discover where to save.
print(f"X-IIIF-Post-Url: {response.headers.get('X-IIIF-Post-Url')}")

# The manifest's metadata block summarises the deposit itself.
for pair in manifest.get("metadata", []):
    label = next(iter(pair["label"].values()))[0]
    value = next(iter(pair["value"].values()))[0]
    print(f"  {label}: {value}")

print(f"\n{len(manifest.get('items', []))} canvases")
for canvas in manifest.get("items", [])[:5]:
    body = canvas["items"][0]["items"][0].get("body", {})
    kind = body.get("type", "-")
    # A canvas with behavior "placeholder" has no real painting body: the file is not an image,
    # video or audio, so it is reachable through the canvas's rendering link instead.
    if canvas.get("behavior") == ["placeholder"]:
        kind = f"placeholder ({canvas['rendering'][0]['format']})"
    print(f"  {kind:<28} {body.get('id', '')}")

# Ranges come from the METS logical structMaps. Type, Name and id in a Range's metadata are how
# it is matched back to the structMap division it came from - keep them.
for range_ in manifest.get("structures", []):
    label = next(iter(range_["label"].values()))[0]
    print(f"\nRange: {label} ({len(range_.get('items', []))} items)")

# Posting it back rewrites the logical structMaps and NOTHING else: canvases are not created,
# deleted or reordered, and no file is touched. Here we send the manifest back unchanged, which
# is a no-op - in real use an editor would have rearranged `structures` first.
result = post(token_url, manifest)
print(f"\nPosted manifest back: {result.status_code} (204 means accepted)")
