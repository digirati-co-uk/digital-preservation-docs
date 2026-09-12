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
