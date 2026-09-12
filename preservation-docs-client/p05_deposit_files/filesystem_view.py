"""
What is actually in the deposit's workspace, as the API sees it.

The API caches this view (in __METSlike.json in the workspace) because listing a large deposit is
expensive. You put files into S3 yourself, so the API does not know they are there until it looks
again: refresh=true makes it look.
"""
from p04_deposits.ensure_deposit import deposit_slug, ensure_deposit
from preservation import get

deposit = ensure_deposit()
slug = deposit_slug(deposit)

# refresh=true after uploading anything; the cached view would not show it otherwise.
root = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()


def walk(directory, indent=0):
    """WorkingDirectory contains WorkingFiles and more WorkingDirectories, all the way down."""
    print(f"{' ' * indent}{directory['localPath'] or '/'}/")
    for file in directory["files"]:
        digest = file.get("digest") or "(no digest)"
        print(f"{' ' * (indent + 2)}{file['localPath']}  {file.get('size')} bytes  {digest[:12]}")
        for metadata in file.get("metadata", []):
            # Each entry says which tool it came from and when: Siegfried, Brunnhilde, BagIt...
            print(f"{' ' * (indent + 4)}{metadata['type']} from {metadata['source']}")
    for child in directory["directories"]:
        walk(child, indent + 2)


walk(root)

# For a BagIt deposit this tree starts at data/ - it is the layout on disk, not the logical view.
print(f"\nTemplate: {deposit['template']}")
