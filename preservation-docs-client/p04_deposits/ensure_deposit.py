"""
A deposit with a few files in it, for the samples on this and later pages to work with.

Not a sample in its own right - import `ensure_deposit()` from it. Set DOCS_DEPOSIT_ID in your
environment (or .env) to reuse a deposit you already made instead of creating another one; the
samples print the id so you can.
"""
import os

import s3_helpers
import settings
from preservation import get, post

SAMPLE_FILES = [
    ("sample_files/notes.txt", "objects/docs/notes.txt"),
    ("sample_files/about.txt", "objects/about.txt"),
]


def ensure_deposit(template: str = "RootLevel") -> dict:
    """The deposit named by DOCS_DEPOSIT_ID, or a new one with the sample files uploaded."""
    existing = os.environ.get("DOCS_DEPOSIT_ID")
    if existing:
        return get(f"/deposits/{existing}").json()

    deposit = post("/deposits", {
        "type": "Deposit",
        "template": template,
        "submissionText": "Created by the documentation samples",
    }).json()

    # Files go into the workspace with the S3 API, not the Preservation API. ChecksumAlgorithm
    # SHA256 asks S3 to store a digest, which the platform can use when the METS has none yet.
    for local_path, relative_path in SAMPLE_FILES:
        s3_helpers.upload_file(deposit["files"], local_path, relative_path, with_checksum=True)

    print(f"\nDeposit {deposit['id']}")
    print(f"To reuse it in other samples: set DOCS_DEPOSIT_ID={deposit['id'].rstrip('/').rsplit('/', 1)[-1]}")
    return deposit


def deposit_slug(deposit: dict) -> str:
    return deposit["id"].rstrip("/").rsplit("/", 1)[-1]
