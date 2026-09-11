"""
Deliberately simple helpers for calling the Preservation API (and, where a client has access to
it, the Storage API). No error handling, no retries, no async - the point is to show the HTTP
operations as plainly as possible. Each helper prints what it is doing.

Authentication: the API expects a bearer JWT from the identity provider your platform instance
is configured with. The samples obtain one with the standard OAuth2 client_credentials grant
(RFC 6749 section 4.4) against settings.TOKEN_ENDPOINT, and send it as `Authorization: Bearer`.
Every request also carries `X-Client-Identity`, the name the API records as who did what.
"""
import json
import time

import requests

import settings

_token = {"access_token": None, "expires_at": 0}


def get_access_token() -> str:
    """OAuth2 client credentials grant: POST form-encoded credentials to the token endpoint and
    receive a JSON body with access_token and expires_in. Cached until shortly before expiry."""
    if _token["expires_at"] > time.time() + 60:
        return _token["access_token"]

    r = requests.post(
        settings.TOKEN_ENDPOINT,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "scope": settings.SCOPE,
        },
    )
    body = r.json()
    _token["access_token"] = body["access_token"]
    _token["expires_at"] = time.time() + int(body.get("expires_in", 3600))
    return _token["access_token"]


def get_auth_headers() -> dict:
    headers = {
        "Accept": "application/json",
        "X-Client-Identity": settings.CLIENT_IDENTITY,
    }
    if not settings.DISABLE_AUTH:
        headers["Authorization"] = f"Bearer {get_access_token()}"
    return headers


def normalise_path(path: str, host: str = None) -> str:
    """Accept a full URI (as returned in `id` properties) or a path relative to the API host."""
    if path.startswith("http"):
        return path
    host = host or settings.PRESERVATION_API_HOST
    if not path.startswith("/"):
        path = "/" + path
    return f"{host}{path}"


def _verify(uri: str) -> bool:
    """A locally running API uses the ASP.NET development certificate; don't verify it."""
    return "localhost" not in uri


def _log(method: str, uri: str, body=None, extra_headers=None):
    print("-------------------------------------------")
    print(f"{method} {uri}")
    if extra_headers:
        for k, v in extra_headers.items():
            print(f"{k}: {v}")
    if body is not None:
        print(json.dumps(body, indent=2) if not isinstance(body, str) else body)


def get(path: str, params: dict = None, host: str = None, extra_headers: dict = None):
    uri = normalise_path(path, host)
    headers = {**get_auth_headers(), **(extra_headers or {})}
    _log("GET", uri, extra_headers=extra_headers)
    r = requests.get(uri, params=params, headers=headers, verify=_verify(uri))
    print(f"HTTP Status Code: {r.status_code}")
    return r


def head(path: str, host: str = None):
    uri = normalise_path(path, host)
    _log("HEAD", uri)
    r = requests.head(uri, headers=get_auth_headers(), verify=_verify(uri))
    print(f"HTTP Status Code: {r.status_code}")
    return r


def post(path: str, body=None, host: str = None, extra_headers: dict = None):
    uri = normalise_path(path, host)
    headers = {**get_auth_headers(), "Content-Type": "application/json", **(extra_headers or {})}
    _log("POST", uri, body, extra_headers)
    r = requests.post(uri, headers=headers, json=body, verify=_verify(uri))
    print(f"HTTP Status Code: {r.status_code}")
    return r


def put(path: str, body=None, host: str = None):
    uri = normalise_path(path, host)
    headers = {**get_auth_headers(), "Content-Type": "application/json"}
    _log("PUT", uri, body)
    r = requests.put(uri, headers=headers, json=body, verify=_verify(uri))
    print(f"HTTP Status Code: {r.status_code}")
    return r


def patch(path: str, body=None, host: str = None):
    uri = normalise_path(path, host)
    headers = {**get_auth_headers(), "Content-Type": "application/json"}
    _log("PATCH", uri, body)
    r = requests.patch(uri, headers=headers, json=body, verify=_verify(uri))
    print(f"HTTP Status Code: {r.status_code}")
    return r


def delete(path: str, host: str = None):
    uri = normalise_path(path, host)
    _log("DELETE", uri)
    r = requests.delete(uri, headers=get_auth_headers(), verify=_verify(uri))
    print(f"HTTP Status Code: {r.status_code}")
    return r


def wait_for_value(path: str, field: str, value, interval: int = 2, retries: int = 30):
    """Poll the resource at `path` until resource[field] == value (e.g. a Deposit's status
    becoming "new", or an ImportJobResult's status becoming "completed")."""
    print(f"Polling {path} until {field} == {value}")
    for i in range(retries):
        resource = get(path).json()
        found = resource.get(field)
        if found == value:
            print(f"{field} is now {found}")
            return resource
        print(f"{field} is {found}; waiting {interval}s (attempt {i + 1}/{retries})")
        time.sleep(interval)
    print(f"Abandoning polling after {retries} attempts")
    return None


def pprint(obj):
    print(json.dumps(obj, indent=2))
