import os
from dotenv import load_dotenv

load_dotenv()  # environment variables from .env, superseded by real environment variables

# Root of the Preservation API of your platform instance, e.g. https://preservation-api.example
PRESERVATION_API_HOST = os.environ.get("PRESERVATION_API_HOST", "").rstrip("/")
# Root of the Storage API. Most API clients never have access to this.
STORAGE_API_HOST = os.environ.get("STORAGE_API_HOST", "").rstrip("/")

# OAuth2 client credentials. The API accepts a bearer JWT issued by the identity provider your
# platform instance is configured with. The samples obtain one with the standard OAuth2
# client_credentials grant, POSTed to TOKEN_ENDPOINT.
#
# For a Microsoft Entra ID tenant (the provider current deployments use):
#   TOKEN_ENDPOINT = https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
#   SCOPE          = api://<preservation-api-app-id>/.default
TOKEN_ENDPOINT = os.environ.get("TOKEN_ENDPOINT")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
SCOPE = os.environ.get("SCOPE")

# Set to true only when the API you are calling has auth disabled (FeatureFlags:DisableAuth),
# which is how a developer runs it locally. Hosted instances always require a token.
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "false").lower() == "true"

# Sent as X-Client-Identity: the name the API records as createdBy / preservedBy for what you do.
CLIENT_IDENTITY = os.environ.get("CLIENT_IDENTITY", "preservation-docs-samples")

# AWS credentials with access to the deposit working bucket, for putting files into deposits.
AWS_PROFILE = os.environ.get("AWS_PROFILE")
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")

# The repository path (under /repository) that the samples create Archival Groups in.
DOCS_CONTAINER_PATH = os.environ.get("DOCS_CONTAINER_PATH", "docs-examples")


def check() -> list[str]:
    """Configuration problems that would otherwise fail later and less clearly."""
    problems = []
    if not PRESERVATION_API_HOST:
        problems.append("PRESERVATION_API_HOST is not set")
    if not DISABLE_AUTH and not (TOKEN_ENDPOINT and CLIENT_ID and CLIENT_SECRET and SCOPE):
        problems.append("TOKEN_ENDPOINT, CLIENT_ID, CLIENT_SECRET and SCOPE are required unless DISABLE_AUTH is true")
    return problems
