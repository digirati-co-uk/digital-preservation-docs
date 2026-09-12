"""
Finding an Archival Group the samples can safely export.

An export needs an object that already exists. Rather than assume one, look for an Archival Group
that these samples preserved earlier: every deposit that has been preserved records both the
Archival Group it became and the version it made.
"""
import os

import settings
from preservation import get


def preserved_archival_group() -> str:
    """The Archival Group URI of the most recent deposit these samples preserved.

    Set DOCS_ARCHIVAL_GROUP to a path under /repository to use a particular object instead.
    """
    override = os.environ.get("DOCS_ARCHIVAL_GROUP")
    if override:
        return f"{settings.PRESERVATION_API_HOST}/repository/{override.lstrip('/')}"

    page = get("/deposits", params={
        "createdBy": settings.CLIENT_IDENTITY,
        "status": "preserved",
        "showAll": "true",
        "orderBy": "preserved",
        "pageSize": 1,
    }).json()
    if not page["deposits"]:
        raise SystemExit(
            "No Archival Group to export: these samples have not preserved one yet. "
            "Run python -m workflows.w02_preserve_first_time, or set DOCS_ARCHIVAL_GROUP to the "
            "path of an object you may export.")
    return page["deposits"][0]["archivalGroup"]
