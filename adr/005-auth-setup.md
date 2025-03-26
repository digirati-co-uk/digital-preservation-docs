# Auth Setup

This document describes the Authentication setup of Digital presentation. 

## Background 
[RFC 005](../rfcs/005-access-control.md) outlines the requirements for access and authentication and authorization.

This approach has been dictated by Leeds using Applications within Microsoft Azure (also called O365, Entra), these Applications and API 


## Definitions  

Applications and API are registered the same within Azure Application Registrations: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade, both Application and API are registered in the same way, but setup and configuration may differ.

For this development we will use the following:

* **Application:** Application with a user interface such as a web ui.
* **API:** Has no users interface and is access via Application UI or API using an auth token or other authentication method. 
* **Single Sign On:** SSO allows users to access Azure Application via their leeds.ac.uk account.


## Basic Setup overview

In Azure there are THREE applications setup as follows:

**Preservation UI:** Provides a Web UI, access via SSO using leeds.ac.uk account.  Provides a challenge response 

**Preservation API:** API which marshalls data for the UI. Accessed via JWT Bearer token.

**Storage API:** API for storage functions. Accessed via JWT Bearer token.  

Note that thw two APIs has no knowledge of the user session or user details on the UI, the Preservation UI creates a JWT Bearer Token and passes this to Preservation API. The Preservation API passed this JWT Bearer Token to Storage API. 

![over of apps and api](../img/adr-002/app_api_overview.png)



## Example setup using Digirati Azure Applications

This is walk through example of Digirati setting up the application in their Azure tenant.  


### Setup three Application 

These application are setup to reflect typical setup expected by Leeds. 

* Preservation UI:  TestLeedsAppDigirati
* Preservation API: TestLeedsPreservationAPIDigirati
* Storage API: TestLeedsStorageAPIDigirati

![alt](../img/adr-002/digi_app_summary.png)


### Setup UI Application 
This is just an example, exact setup on Leeds may vary. This is only an example of setup for Web UI.

![ui application setup example](../img/adr-002/digi_app_ui_setup.png)


## Setup user / group for Application access

No example/image shown, this allows users to access the application.


![Overview of Digirati Apps](../img/adr-002/digi_app_summary.png)

### Grant Admin Consent 

Under each application, API permissions, grant correct concent of details that you wish the application to have. 

![admin content granting](../img/adr-002/digi_app_admin_concent.png)


### Expose API from Application UI

This allows the Application UI to access downstream APIs and generate tokens for those applications.  This is important as you need the api scope to generate JWT Access Tokens for both Preservation and Storage APIs.


![expose and api](../img/adr-002/digi_expose_apis.png)


### Setup Application 

The Application UI AzureAd Application setting is set as thus:

```
  "AzureAd": {
    "Instance": "https://login.microsoftonline.com/",
    "TenantId": "bc970ba1-ef24-4df6-9e2e-1e94873f345a",
    "ClientId": "3d8bebec-5c12-4ac7-a1c4-d57d7303b011",
    "CallbackPath": "/oauth2/idpresponse",
    "ClientSecret": "<secret if needed>",
    "ScopeUri": "api://3d8bebec-5c12-4ac7-a1c4-d57d7303b011/TestLeedsAppDigiratiScope"
  },
```

Note the "ScopeUri"; this is the Scope used for exposing API on the Azure Application. Very basic C# code to generate an access token is shown below.

```
string[] scopes = ["api://3d8bebec-5c12-4ac7-a1c4-d57d7303b011/TestLeedsAppDigiratiScope"];
string accessToken =  tokenAcquisition.GetAccessTokenForUserAsync(scopes).Result;
```

You need the correct scope to generate an access token which has the "scope" or the right to access the API. The token has the right to access the downstream APIs and nothing else.


### API App Settings
This doesn't need the token scope as UI Applications. But each API does need its own ClientID set. 

```
  "AzureAd": {
    "Instance": "https://login.microsoftonline.com/",
    "TenantId": "<tenant id>",
    "ClientId": "<client id>"
    "Audience":  "api://<client id>" ,
  },
```

## Generate CLI User access token

This is based on the setup of the application setup and the permissions on the applications.  This example uses the Digirati APP and two  APP apis configured.  You need to login into the Scope (the App) and generated an access token for that scope. This makes sense as this access token can only be used for that app/scope. This requires azure CLI (https://learn.microsoft.com/en-us/cli/azure/)  to be installed. 


Step1:  login to the scope
```
 az login --scope api://3d8bebec-5c12-4ac7-a1c4-d57d7303b011/TestLeedsAppDigiratiScope
```

Step2: Generate a token the app and scope
```
 az account get-access-token  /
 --resource "api://3d8bebec-5c12-4ac7-a1c4-d57d7303b011" / 
 --scope "api://3d8bebec-5c12-4ac7-a1c4-d57d7303b011/TestLeedsAppDigiratiScope" / 
 --query accessToken
 ```

 This generates a token as below:


![digirati cli token example](../img/adr-002/digi_token_cli_example.png)


Note:  You can generate token without --scope, but this will give a token which will no have access to the application api and will return a 401 (not authorized).

#### example using cli access token
Below is a basic example of using a CLI access token to hit an endpoint on Preservation API. 

![client access token example postman](../img/adr-002/cli_token_example.png)


## Generate Machine Access Token

There is likely alternatives to Application B2B connections and this is one of them. This method uses the Client Secret to generate an access token from the application itself to have a token that can access the APIs.

### Setup the Application 

The application must be setup to have permissions to itself. Or you get odd errors saying Application X does not have access to Application X.

### Create an App Role 

Create an app role is so it can appears in Claims. You can then tell where the Token is coming from. Also abilities to apply different permissions to different apps. 

![Add a new app role](../img/adr-002/app_add_role.png)

### Assign this Role to the Application

Assign this role to the Application; effectively giving the application rights to itself. Also remember to assign admin consent. 

![assign the app role](../img/adr-002/app_role_api_perms.png)
![grant admin to role type](../img/adr-002/app_role_grant.png)

### Generate a Machine Token 

Example here uses Postman to generate an access token for the scope and resource using the application secret key.

 https://login.microsoftonline.com/<TENANT-ID>/oauth2/token

https://login.microsoftonline.com/bc970ba1-ef24-4df6-9e2e-1e94873f345a/oauth2/token

![alt text](../img/adr-002/postman_app_b2b.png)


  *  grant_type:    client credentials
  *  client_id:    client id of the application
  *  client_secret:  client secret of the application
  *  scope:  this is the audience value used by APIs (or Scope in .NET)
  *  resource: The Application url.  

**Token generated**

This will give a token like this. 

![post generated machine access token](../img/adr-002/postman_app_token.png)


### Machine Token decoded

The machine token generated is NOT a user token so will not have some of the claims and fields you might expect from a user token. For example there will be no email, first lat names. 

This token does have the role (API) defined and this could be used to define a source if that is required. 

![decoded machine token with role API](../img/adr-002/decoded_machine_token.png)


### Using Machine Token

A machine token can be used to access the APIs, but it must be accompanied by a header value "X-Client-Identity" with a string value of the application, system or identification of caller. There is an authorization filter in place which will deny calls if the header value is not supplier.  

A curl example would be 

```
curl --location --request PUT 'https://localhost:7228/repository/test000009' \
--header 'X-Client-Identity: myapplication' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer eyJ0eXAiOiJK..........kjknM-_55g' \
--data '{
    "type": "Container",
    "name":  "test000009"
```
-------------------

## Limitations and Known Issues

These limitations affect the current Azure AD authentication implemented. Our Auth implementations may vary. 
This explanation is for tokens generated for direct access to APIs from no Web-UI interface (also called Preservation-UI).

#### Machine Tokens

Machine tokens can't be customized on creation; you can't provide parameters that will be included in the token. This means that a machine token is not identifiable nor can its source be understood when used to contact the APIs.

Machine token are generated for the App Id and the Audience/Scope. Only one Audience can be configured on the C# Code AppSettings for an API (see example above). The Audience is generated by Token generation of the Web-UI and the API expects this audience. So that means you can't use a different application to generate token for that API.  You could in theory use a different API implementation using a difference audience, but the application stack/cache would have to handle multiple APIs. 

In order to generate token with examples provided, an Application Secret is required. Multiple secrets can be generated per application which have a limited life span (suggested 6 months by Microsoft).

### User Tokens 

User tokens do have identifiable content; basic user information such as name and email. 

####  Token Life

User tokens are short lived (an hour by default). There are application stacks (MSAL for example see https://learn.microsoft.com/en-us/entra/identity-platform/msal-overview) which will auto-refresh token for long term user.

## EOF

