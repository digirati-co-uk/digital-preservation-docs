"""
A Deposit as a IIIF Manifest.

GET /deposits/{id}/iiif is authenticated and answers with a redirect to a tokenised URL. That
tokenised URL needs no Authorization header, which is what lets you hand it to a viewer running
in a browser. Treat the token as a secret: the manifest describes every file in the deposit.

Requires the instance to have EnableIiifMediaEndpoints switched on. With the flag off,
/deposits/{id}/iiif answers 404.
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
    # Every canvas is a placeholder showing the file's format; the manifest doesn't link to a
    # deposit's files. What it says about each file is in the canvas's metadata.
    label = next(iter(canvas["label"].values()))[0]
    details = {next(iter(m["label"].values()))[0]: next(iter(m["value"].values()))[0]
               for m in canvas.get("metadata", [])}
    print(f"  {label:<40} {details.get('Preservation: Media type', '-')}")
    for condition in canvas.get("accessConditions", []):
        print(f"      {condition['type']}: {condition['value']}")

# Ranges come from the METS logical structMaps, and from the folders below objects/ when there are any.
for range_ in manifest.get("structures", []):
    label = next(iter(range_["label"].values()))[0]
    print(f"\nRange: {label} ({len(range_.get('items', []))} items)")
