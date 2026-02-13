# About

This script provides a quick reference guide for the **OAuth 2.0 Web Server Flow with PKCE** against a Salesforce org.

It demonstrates:

* Generating a PKCE `code_verifier` and `code_challenge`
* Building the authorization URL
* Running a local callback server
* Exchanging the authorization code for tokens
* Parsing and returning the final OAuth token response

The direct Custom Domain URL is used as it is an identicial process between Production (`login.salesforce.com`), Development Edition (`login.salesforce.com`), and Sandbox orgs (`test.salesforce.com`). 

Kindly adjust your instance (custom domain), client_id (key), and client_secret (sec) within the script: 

```
INSTANCE: str = "https://sample-dev-ed.trailblaze.my.salesforce.com"
KEY: str = '3MVG9JJwBBbcN47K5GDwV5CMZb7YPOak6qFo8qEU0AWObcE2yBbhJtF0v18keWmZHcFkED7b3vso3NU46NIjo'
SEC: str = '99FBD74CEE363E817535EA8B13BFD11EF6AU04YSPTQS27RHFDV9MJEMPQDECKIP'
```

---

# OAuth 2.0 Web Server Flow with PKCE – Step-by-Step


## 1. OAuth Flow Started

The flow begins with the following configuration:

```json
{
  "instance": "https://sample-dev-ed.trailblaze.my.salesforce.com",
  "client_id": "3MVG9JJwBBbcN47K5GDwV5CMZb7YPOak6qFo8qEU0AWObcE2yBbhJtF0v18keWmZHcFkED7b3vso3NU46NIjo",
  "redirect_uri": "http://localhost:8000/callback"
}
```

### Parameters

| Field          | Description                                                |
|----------------|------------------------------------------------------------|
| `instance`     | Base URL of the Salesforce org                             |
| `client_id`    | External Connected App Consumer Key                        |
| `redirect_uri` | Callback endpoint registered in the External Connected App |

---

## 2. PKCE Generated

The script generates a secure PKCE pair:

```json
{
  "code_verifier": "IziO58ClrgKUcNFcAITz536MDc9CFPRao51aNy2oJJgcpjx50Teodw",
  "code_challenge": "JmR5pIeKlldrAdhAodjTAjebTZJyeCIwf3RJ2H_ySOs",
  "challenge_method": "S256"
}
```

### How It Works

1. Generate random bytes using `os.urandom()` which is suitable for cryptographic uses.
2. Base64URL encode → `code_verifier`
3. SHA-256 hash the verifier
4. Base64URL encode the hash → `code_challenge`

`S256` indicates SHA-256 is used. This is the method Salesforce uses.

Alternatively, the use of the `/services/oauth2/pkce/generator` endpoint is possible, but is not typical unless on embedded devices due to the network overhead and additional points of failure.

---

## 3. Authorization URL Built

Authorization endpoint:

```
https://sample-dev-ed.trailblaze.my.salesforce.com/services/oauth2/authorize
```

Query parameters:

```json
{
  "client_id": "...",
  "redirect_uri": "http://localhost:8000/callback",
  "response_type": "code",
  "code_challenge": "JmR5pIeKlldrAdhAodjTAjebTZJyeCIwf3RJ2H_ySOs",
  "code_challenge_method": "S256"
}
```

Final authorization URL:

```
https://sample-dev-ed.trailblaze.my.salesforce.com/services/oauth2/authorize?client_id=...&redirect_uri=...&response_type=code&code_challenge=...&code_challenge_method=S256
```

The script then opens the system browser to initiate login.

---

## 4. Callback Server Started

A local HTTP server is started:

```json
{
  "hostname": "localhost",
  "port": 8000,
  "path": "/callback"
}
```

Listening on:

```
http://localhost:8000/callback
```

---

## 5. Authorization Code Received

Salesforce redirects back with:

```
/callback?code=aPrxSQ3aaqvXvXS1YFs99kfElnR6laQluNi_m0uNK6SFMvIDfRt57JVu3fwgRWJCHQOSojJ8PXy_VW4ohqzxl.LxsGrGRPE=
```

Extracted:

```json
{
  "authorization_code": "aPrxSQ3aaqvXvXS1YFs99kfElnR6laQluNi_m0uNK6SFMvIDfRt57JVu3fwgRWJCHQOSojJ8PXy_VW4ohqzxl.LxsGrGRPE="
}
```

---

## 6. Token Request Prepared

Token endpoint:

```
https://sample-dev-ed.trailblaze.my.salesforce.com/services/oauth2/token
```

Form payload:

```json
{
  "grant_type": "authorization_code",
  "code": "aPrxSQ3aaqvXvXS1YFs99kfElnR6laQluNi_m0uNK6SFMvIDfRt57JVu3fwgRWJCHQOSojJ8PXy_VW4ohqzxl.LxsGrGRPE=",
  "client_id": "3MVG9JJwBBbcN47K5GDwV5CMZb7YPOak6qFo8qEU0AWObcE2yBbhJtF0v18keWmZHcFkED7b3vso3NU46NIjo",
  "redirect_uri": "http://localhost:8000/callback",
  "code_verifier": "IziO58ClrgKUcNFcAITz536MDc9CFPRao51aNy2oJJgcpjx50Teodw",
  "client_secret": "********"
}
```

**IMPORTANT**: The `code_verifier` must match the `code_challenge` sent earlier.

---

## 7. Token Response Received

Status: `200 OK`

Raw response:

```json
{
  "access_token": "00Dak0000000000!X5uk20JAGuO3FR8gPDO607BR6ffWfaFIKQb7YOCBw08b3FE0TDG1fVp8aeCTq25OdC0B9yD8W1Ajiv46Y3Pm3o37j51qB3LK",
  "refresh_token": "5AeFS689N62y7ZV4zE1skBM0ziB7K9euw1s19p8eSX7h.rizGM1_QQQ.vch3u7yYl.7kfdVKK03W.rxTPYBmskM",
  "signature": "vXu9CpiCNIXtX2EH4BmWH583firy5XH9ZpU6AVJETd0=",
  "scope": "refresh_token sfap_api web api",
  "instance_url": "https://sample-dev-ed.trailblaze.my.salesforce.com",
  "id": "https://login.salesforce.com/id/00Dak0000000000EAA/005ak0000000000AAA",
  "token_type": "Bearer",
  "issued_at": "1770952407907",
  "api_instance_url": "https://api.salesforce.com"
}
```

---

## 8. OAuth Flow Complete

Final parsed token object:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "instance_url": "https://sample-dev-ed.trailblaze.my.salesforce.com",
  "id_url": "https://login.salesforce.com/id/00Dak0000000000EAA/005ak0000000000AAA"
}
```

---

# What You Get

| Field           | Description                                  |
|-----------------|----------------------------------------------|
| `access_token`  | Used to authorize API calls                  |
| `refresh_token` | Used to obtain new access tokens             |
| `instance_url`  | Base URL for REST API calls                  |
| `id`            | Identity endpoint for the authenticated user |
| `scope`         | Granted OAuth scopes                         |
| `issued_at`     | Token issue timestamp (epoch ms)             |

---

# Summary Flow Diagram

1. Generate PKCE (`code_verifier`, `code_challenge`)
2. Redirect user to `/services/oauth2/authorize`
3. User logs in & approves
4. Receive `authorization_code`
5. POST to `/services/oauth2/token`
6. Receive `access_token` + `refresh_token`
7. Call Salesforce APIs using `Authorization: Bearer <access_token>`

---

# Security Notes

* Never expose `client_secret` in public clients.
* Store `refresh_token` securely.

