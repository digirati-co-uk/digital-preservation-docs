# Preservation API samples

Runnable Python that accompanies the documentation site. Each `pNN_topic/` directory matches
a page of the API documentation.

```bash
cp example.env .env      # and fill it in
pip install -r requirements.txt
python p02_repository/browse_repository.py
```

`preservation.py` holds the HTTP helpers and the Entra ID client-credentials auth;
`s3_helpers.py` puts files into deposit workspaces with boto3. The code is intentionally
simple - no error handling, no async - so that the HTTP operations are easy to read.
