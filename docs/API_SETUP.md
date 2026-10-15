# Getting store API credentials

Only stores with a **free, official** API are wired up. Everything else is shown
as "Prices coming soon" in the UI.

| Store | Official free API | Status in app |
| --- | --- | --- |
| Kroger (and Kroger-family banners) | [Kroger Public API](https://developer.kroger.com) | Live once keys are set |
| Walmart | [Walmart.io Affiliate API](https://walmart.io/docs/affiliates/v1/introduction) | Live once keys are set |
| Target, Aldi, Whole Foods, Trader Joe's | None | Prices coming soon |

All credentials live in `.env` (git-ignored) or your host's secret manager, are
read only by the backend, and are never sent to the browser.

## Kroger

1. Create a developer account at <https://developer.kroger.com> and sign in.
2. **Register an application** (environment: *Production*). Enable the **Product**
   and **Location** APIs. The redirect URI is not used by this app (we only use the
   client-credentials flow); any valid URL such as `http://localhost:8000` is fine.
3. Copy the app's **Client ID** and **Client Secret** into `.env`:

   ```env
   KROGER_CLIENT_ID=your-client-id
   KROGER_CLIENT_SECRET=your-client-secret
   ```

How it's used: the backend exchanges the id/secret for a token
(`POST /v1/connect/oauth2/token`, scope `product.compact`), resolves the user's ZIP
to the nearest store (`GET /v1/locations?filter.zipCode.near=`), and searches
products at that store (`GET /v1/products?filter.term=&filter.locationId=`).
Kroger only returns prices when a store location is given, so users must enter a
ZIP (or you can set `DEFAULT_ZIP_CODE`).

## Walmart

1. Go to <https://walmart.io>, click **Login**, and sign in with a Walmart.com
   account (create one if needed). Create an **application** for the Affiliate API.
2. Generate an RSA key pair **outside this repo** (from Walmart's
   [key tutorial](https://walmart.io/key-tutorial)):

   ```bash
   mkdir -p ~/.secrets && cd ~/.secrets
   openssl genrsa -out WM_IO_my_rsa_key_pair 2048
   openssl pkcs8 -topk8 -inform PEM -in WM_IO_my_rsa_key_pair -outform PEM -out WM_IO_private_key.pem -nocrypt
   openssl rsa -in WM_IO_private_key.pem -pubout > WM_IO_public_key.pem
   cat WM_IO_public_key.pem   # paste the body (without BEGIN/END lines) into the portal
   ```

3. Upload the public key in the Walmart.io dashboard. You then get a
   **Consumer ID** and a **key version** (usually `1`).
4. Configure `.env`:

   ```env
   WALMART_CONSUMER_ID=your-consumer-id
   WALMART_KEY_VERSION=1
   WALMART_PRIVATE_KEY_PATH=~/.secrets/WM_IO_private_key.pem
   # optional, for affiliate tracking links:
   WALMART_PUBLISHER_ID=
   ```

   On a hosting provider without files, put the PEM contents in a
   `WALMART_PRIVATE_KEY` secret instead (newlines may be written as `\n`).

How it's used: every request is signed (SHA256withRSA over consumer id,
timestamp and key version) and sent to
`GET https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search?query=`.
Signatures expire after 180 seconds, so they're generated per request. Prices are
Walmart.com online prices (the search API is not store-specific).

## Keeping keys out of the public repo

- Never commit `.env`, `*.pem` or `*.key`; they're in `.gitignore`.
- `pre-commit install` enables [gitleaks](https://github.com/gitleaks/gitleaks) and
  a private-key detector that block commits containing secrets. CI runs gitleaks
  on every push/PR too.
- If a key is ever committed, **rotate it** in the store's portal; deleting the
  commit isn't enough once it's public.
