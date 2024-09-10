# Access Control RFC

This RFC addresses how we will handle access control (authentication and authorization) for the following resources:

* Preservation API (P-API)
* Storage API (S-API)
* Digital Preservation Web UI (UI, below)
* Fedora

Key considerations:
* Security
* Simplicity
* Standards based (OAuth2 and OIDC)
* Identity of users accurately represented in Fedora, ie they are independent of any source identity provider as they must be meaningful if Fedora alone is restored.

## Proposed Solution

> [!NOTE]
> Assuming AzureAD as identity provider

### Summary 

A high level summary is:

* User provisioned and management is an external concern to all systems mentioned above.
* UI will use OAuth2 authorization code flow. `id_token` will contain user identity.
* S-API and P-API will use OAuth2 client credentials flow. `access_token` will contain user identity.
* All interactions with Fedora will go via the S-API. S-API will manage access and dictate `fedora:createdBy` and `fedora:lastModifiedBy` values.

### Human Interactions

UI will use the oauth2 [authorization code](https://oauth.net/2/grant-types/authorization-code/) grant, the end result of which is that the UI will have an [`id_token`](https://auth0.com/docs/secure/tokens/id-tokens), to identify the current user, and an [`access_token`](https://auth0.com/docs/secure/tokens/access-tokens) that can be used when accessing S-API and P-API.

### Machine to Machine

Third party services, e.g. Goobi or IIIF-Builder, will need a token to access the P-API or the S-API.

These services will use oauth2 [client credentials](https://oauth.net/2/grant-types/client-credentials/) grant to get an `access_token` for presenting to the P-API and S-API. As mentioned above the acquisition of the `access_token` is an external concern - when provided to either API the token will be verified before allowing access.

For the purposes of security both the P-API and S-API will share a single "security domain", in OIDC terms they'll be a single [audience (`aud`)](https://www.rfc-editor.org/rfc/rfc7519#section-4.1.3).

Custom claims within the token will be able to govern what access is available, e.g. whether S-API and P-API access is allowed. Exactly what these claims are will be addressed as we progress with the project along with any custom scopes.

### Fedora

The `access_token` provided to S-API will contain the identify of the caller as the [subject (`sub`)](https://www.rfc-editor.org/rfc/rfc7519#section-4.1.2 claim). This may be a human indirectly using the API via UI interactions, or a machine directly consuming the API, as mentioned above this identity needs to be accurately represented in the underlying OCFL document.

Fedora supports a few different [authentication and authorization](https://wiki.lyrasis.org/display/FEDORA6x/Authentication+and+Authorization) mechanisms for access control. However we should conting to use "Fedora as a means to OCFL" as outlines in [RFC 001](./001-what-is-stored-in-fedora.md#fedora-as-a-means-to-ocfl). With regards to access-control it means having all access-control logic contained within the S-API, with it enforcing access and indicating to Fedora which user carried out each action.

This approach avoids Fedora managing an ever growing list of users as that concern is left to the S-API. The S-API uses administrator credentials when interacting with Fedora, by default Fedora has a set of 'server managed triples' (namely [fedora:created](https://fedora.info/definitions/v4/2016/10/18/repository#created), [fedora:createdBy](https://fedora.info/definitions/v4/2016/10/18/repository#createdBy), [fedora:lastModified](https://fedora.info/definitions/v4/2016/10/18/repository#lastModified) and [fedora:lastModifiedBy](https://fedora.info/definitions/v4/2016/10/18/repository#lastModifiedBy)) which are populated. The `fedora:createdBy` and `fedora:lastModifiedBy` will default to the user making the request, e.g. `"fedoraAdmin"`. However we can [configure](https://wiki.lyrasis.org/display/FEDORA6x/Updating+Server+Managed+Triples) Fedora to allow us to modify these values by making a `text/turtle` request like:

```
PREFIX fedora: <http://fedora.info/definitions/v4/repository#>
<>
 fedora:createdBy "frodo";
 fedora:lastModifiedBy "frodo";
```

### Questions

* According to [MSDN](https://learn.microsoft.com/en-us/azure/active-directory-b2c/tokens-overview#claims) the `"sub"` claim from AzureAD is _"By default....populated with the object ID of the user in the directory."_. The example given (`884408e1-2918-4cz0-b12d-3aa027d7563b`) does not immediately identify the user, something like `dlip/frodo` or `dlip/goobi` would be more descriptive. Is it possible to configure AzureAD to return something more meaningful as `"sub"`, or do we need something else - and custom claim or some sort of lookup service?
* What would the process be for creating 'users', both human and machine, in AzureAD?
* Would we want to use some semblance of Fedora's built in [Web Access Control](https://wiki.lyrasis.org/display/FEDORA6x/Web+Access+Control)? This could make the interactions with S-API more complex so I think it's best to keep it all in S-API. If we wanted to implement something like this, we would need multiple 'FedoraAdmins' as these are the credentials presented to Fedora.
* Will we require any 'anonymous' access to the UI?
* How will automated tests authenticate with identity provider for testing UI, is there restrictions requiring MFA?

### Implementation Detail

Given we are using dotnet and AzureAD the best way to implement this is via [Microsoft Authentication Library (MSAL)](https://learn.microsoft.com/en-us/entra/identity-platform/msal-overview) as this can do a lot of the heavy lifting on our behalf - e.g. token acquisition, expory, caching, refreshing etc.

For the UI we could consider offloading the authentication to the [AWS LoadBalancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html) but I think the implementation saving would be negligible if MSAL is as simple to implement as documented.

The expectation is that we will use RS256 signed tokens as this seems to be what [AzureAD](https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration) configuration supports, although alternative algorithms will be supported if required.

### Next Steps

If the above proposal is accepted the immediate next steps would be creation of AzureAD resources.

We'll need an application/tenant (terminology?) created for UI and APIs. Digirati will need to provide some details (e.g. redirectUrl) or have access to update these. We would also need relevant details for configuring clients (e.g. scopes, clientId, clientSecret, endpoints etc to configure the client.
* Creation of AzureAD application for APIs. As above we would need relevant details to configure client.
* Initially these clients would be for the development environment only; we can either share the same client Ids for local development and the 'dev' environment in AWS.
* 'Machine' users will need to be created for:
  * Automated tests
  * Local development
  * ...anything else?
