"""
An e-thesis: save it, then update it.

What a script that deposits theses does, with no XML written anywhere. The platform writes the
METS, because the deposit is made from a template.

  python -m workflows.w09_etheses save      # a new thesis: the PDF and a metadata sidecar
  python -m workflows.w09_etheses update    # a new version, with the sidecar replaced

Add --review to stop once the files are described, and leave a person to preserve the deposit in
the UI. Without it, the script preserves the deposit itself.

A thesis here is two files under objects/: the thesis, and a "sidecar" file of metadata about it.
The sidecar's name and format below are placeholders.

Set ETHESES_CONTAINER_PATH (default "etheses") for where theses live in the repository, and
DOCS_ARCHIVAL_GROUP_NAME (default "my-thesis") for which thesis this run works on.
"""
import json
import os
import sys
import time

import s3_helpers
import settings
from preservation import get, head, post, pprint, put, wait_for_value

THESIS = ("sample_files/thesis.pdf", "objects/thesis.pdf")
SIDECAR = "objects/thesis-metadata.json"

container = os.environ.get("ETHESES_CONTAINER_PATH", "etheses")
name = os.environ.get("DOCS_ARCHIVAL_GROUP_NAME", "my-thesis")
archival_group = f"{settings.PRESERVATION_API_HOST}/repository/{container}/{name}"


def save():
    """A new thesis, preserved as v1."""
    # The container theses live in. It only needs making once.
    if head(f"/repository/{container}").status_code == 404:
        put(f"/repository/{container}", {"type": "Container", "name": "E-theses"})

    # A templated deposit: objects/, metadata/ and a METS file the platform wrote and may edit.
    r = post("/deposits", {
        "type": "Deposit",
        "template": "RootLevel",
        "archivalGroup": archival_group,
        "archivalGroupName": "On the preservation of theses",
        "submissionText": "Deposited by the e-theses sample script",
    })
    deposit = created(r, "Deposit not created")

    # The thesis and its sidecar. No checksums needed: the pipeline produces them.
    local_path, relative_path = THESIS
    s3_helpers.upload_file(deposit["files"], local_path, relative_path)
    upload_sidecar(deposit, {"title": "On the preservation of theses", "author": "A. Student"})

    describe_and_finish(deposit)


def update():
    """A new version of a thesis that is already preserved, with its sidecar replaced."""
    # Export the thesis into a new deposit: every file is copied into the workspace. Theses are
    # small, so this is cheap, and it means the pipeline sees the whole object again.
    r = post("/deposits/export", {"type": "Deposit", "archivalGroup": archival_group})
    deposit = created(r, "Export not accepted")
    deposit = wait_for_value(f"/deposits/{slug_of(deposit)}", "status", "new", interval=5, retries=60)
    if deposit is None:
        raise SystemExit("The export has not finished.")

    # Replace the sidecar: here, to correct the author's name.
    upload_sidecar(deposit, {"title": "On the preservation of theses", "author": "A. N. Student"})

    describe_and_finish(deposit)


def describe_and_finish(deposit):
    """Run the pipeline, make sure the METS describes every file, then preserve or hand over."""
    slug = slug_of(deposit)

    # The pipeline identifies formats, scans for viruses, and writes what it finds to metadata/.
    # 204 No Content: the work is queued, not done.
    r = post(f"/deposits/{slug}/pipeline")
    if r.status_code != 204:
        pprint(r.json())
        raise SystemExit(f"Pipeline not started: {r.status_code}")
    wait_for_pipeline(slug)

    # Put every file, with what the pipeline found out about it, into the METS. The pipeline has
    # done this already for what it saw; doing it again is harmless, and catches anything it missed.
    filesystem = get(f"/deposits/{slug}/filesystem", params={"refresh": "true"}).json()
    paths = [path for path in file_paths(filesystem) if path.startswith(("objects/", "metadata/"))]
    mets_etag = get(f"/deposits/{slug}").json()["metsETag"]
    r = post(f"/deposits/{slug}/mets", paths, extra_headers={"If-Match": mets_etag})
    if r.status_code >= 400:
        pprint(r.json())
        raise SystemExit(f"Could not add to METS: {r.status_code}")

    if "--review" in sys.argv:
        print(f"\nDeposit {slug} is ready for a person to check and preserve in the UI.")
        return

    # Read the diff before running it. Nothing should be deleted by either command here.
    r = get(f"/deposits/{slug}/importjobs/diff")
    if r.status_code != 200:
        pprint(r.json())
        raise SystemExit(f"No diff: {r.status_code}")
    job = r.json()
    for operation in ["binariesToAdd", "binariesToPatch", "binariesToDelete", "containersToDelete"]:
        print(f"  {operation}: {[entry['id'].rsplit('/', 1)[-1] for entry in job[operation]]}")
    if job["binariesToDelete"] or job["containersToDelete"]:
        raise SystemExit("The diff wants to delete things. Stop and work out why before preserving.")

    r = post(f"/deposits/{slug}/importjobs", job)
    result_id = slug_of(created(r, "Import Job not accepted"))
    final = wait_for_value(f"/deposits/{slug}/importjobs/results/{result_id}", "status", "completed",
                           interval=3, retries=40)
    if final is None:
        pprint(get(f"/deposits/{slug}/importjobs/results/{result_id}").json())
        raise SystemExit("The Import Job has not completed.")
    print(f"\n{container}/{name} preserved as {final['newVersion']}")


def upload_sidecar(deposit, metadata):
    s3_helpers.upload_text(deposit["files"], json.dumps(metadata, indent=2), SIDECAR,
                           content_type="application/json")


def wait_for_pipeline(slug):
    # waiting -> processing -> metadataCreated -> completed. `metadataCreated` means the tools have
    # run but their output is not yet back in the deposit, so it is not the state to stop at.
    for _ in range(60):
        jobs = get(f"/deposits/{slug}/pipelinerunjobs").json()
        status = jobs[-1]["status"] if jobs else "(none yet)"
        print(f"Pipeline status: {status}")
        if status == "completed":
            return
        if status == "completedWithErrors":
            pprint(jobs[-1])
            raise SystemExit("The pipeline reported errors.")
        time.sleep(5)
    raise SystemExit("The pipeline has not finished.")


def file_paths(directory):
    paths = [file["localPath"] for file in directory["files"]]
    for child in directory["directories"]:
        paths += file_paths(child)
    return paths


def created(response, failure):
    if response.status_code != 201:
        pprint(response.json())
        raise SystemExit(f"{failure}: {response.status_code}")
    return response.json()


def slug_of(resource):
    return resource["id"].rstrip("/").rsplit("/", 1)[-1]


if __name__ == "__main__":
    commands = {"save": save, "update": update}
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command not in commands:
        raise SystemExit("Say which: save or update")
    commands[command]()
