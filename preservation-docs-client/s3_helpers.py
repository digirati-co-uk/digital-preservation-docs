"""
Files are put into a Deposit's workspace with the AWS S3 API, not the Preservation API.
These helpers do the minimum needed by the samples.
"""
import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import boto3

import settings

_session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
s3 = _session.client("s3")


def split_s3_uri(s3_uri: str):
    """s3://bucket/some/key/ -> ("bucket", "some/key")"""
    parsed = urlparse(s3_uri)
    return parsed.netloc, parsed.path.lstrip("/").rstrip("/")


def upload_file(deposit_files_uri: str, local_path: str, relative_path: str, with_checksum: bool = False):
    """Upload a local file to `relative_path` within the Deposit workspace given by the
    Deposit's `files` property. If with_checksum is True, S3 computes and stores a SHA256
    checksum on the object, which the API can read when no METS file supplies one."""
    bucket, prefix = split_s3_uri(deposit_files_uri)
    key = f"{prefix}/{relative_path.lstrip('/')}"
    content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    extra = {"ContentType": content_type}
    if with_checksum:
        extra["ChecksumAlgorithm"] = "SHA256"
    print(f"Uploading {local_path} to s3://{bucket}/{key}")
    s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
    return f"s3://{bucket}/{key}"


def upload_text(deposit_files_uri: str, text: str, relative_path: str, content_type: str = "text/plain"):
    bucket, prefix = split_s3_uri(deposit_files_uri)
    key = f"{prefix}/{relative_path.lstrip('/')}"
    print(f"Uploading text to s3://{bucket}/{key}")
    s3.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), ContentType=content_type)
    return f"s3://{bucket}/{key}"


def list_keys(deposit_files_uri: str):
    bucket, prefix = split_s3_uri(deposit_files_uri)
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix + "/"):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    for k in keys:
        print(k)
    return keys


def delete_key(s3_uri: str):
    bucket, key = split_s3_uri(s3_uri)
    print(f"Deleting s3://{bucket}/{key}")
    s3.delete_object(Bucket=bucket, Key=key)


def sha256_of_file(local_path: str) -> str:
    h = hashlib.sha256()
    with open(local_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def size_of_file(local_path: str) -> int:
    return Path(local_path).stat().st_size
