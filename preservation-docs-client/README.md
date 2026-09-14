# Preservation API samples

Runnable Python that accompanies the documentation site. Each `pNN_topic/` directory matches
a page of the API documentation.

```bash
cp example.env .env      # and fill it in
pip install -r requirements.txt
python -m p03_repository.browse_repository
```

Run the samples as modules (`python -m ...`) from this directory, so that the shared
`settings.py` and `preservation.py` at the top level are importable.

`preservation.py` holds the HTTP helpers and the OAuth2 client-credentials auth (see
[Authentication](https://digirati-co-uk.github.io/digital-preservation-docs/preservation-api/authentication/));
`s3_helpers.py` puts files into deposit workspaces with boto3. The code is intentionally
simple - no error handling, no async - so that the HTTP operations are easy to read.

## Running them against a real instance

These samples do real work: they create Deposits, upload files, and preserve Archival Groups. Point
them at a development instance, never production, and check `PRESERVATION_API_HOST` before you run.

Two things to know if you run several in a row:

- **Only one active Deposit may exist for an Archival Group at a time.** A sample that leaves one
  behind will block the next with a `409`. Set `DOCS_ARCHIVAL_GROUP_NAME` to give a sample its own
  object, or delete the deposits you are finished with.
- **A Deposit is good for exactly one Import Job.** Once a sample has preserved something, that
  deposit cannot be used again; `DOCS_DEPOSIT_ID` is for sharing a *working* deposit between
  samples, not one that has already been preserved.

Environment variables beyond `example.env`:

| Variable | What it does |
|---|---|
| `DOCS_DEPOSIT_ID` | Reuse an existing deposit instead of creating one. |
| `DOCS_ARCHIVAL_GROUP_NAME` | The object name the import-job samples work on, under `DOCS_CONTAINER_PATH`. |
| `DOCS_ARCHIVAL_GROUP` | A full path under `/repository` for the export samples to export. |
