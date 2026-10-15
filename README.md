## Grocery Comparison App (Live Store APIs)

Compares grocery prices across US chains using the stores' **official, free APIs**.
Prices are fetched live on every search; there is no price database.

| Store | Data source | Status |
| --- | --- | --- |
| Walmart | [Walmart.io Affiliate API](https://walmart.io/docs/affiliates/v1/introduction) | Live (needs keys) |
| Kroger | [Kroger Public API](https://developer.kroger.com) | Live (needs keys + ZIP) |
| Target, Aldi, Whole Foods, Trader Joe's | No free official API | "Prices coming soon" |

Stores without keys show as **Not configured**. The app never invents prices
unless you explicitly turn on `USE_MOCK_DATA=true`, and even then they're
labelled "Demo data".

### Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pre-commit install               # blocks commits containing secrets

cp .env.example .env             # then fill in your keys (see docs/API_SETUP.md)
uvicorn backend.main:app --reload
```

Open <http://localhost:8000>. The backend serves the frontend, so don't open
`frontend/index.html` directly. To host the frontend separately, set
`window.GROCERY_API_BASE_URL` before `app.js` loads and add that origin to
`CORS_ALLOW_ORIGINS`.

Run the tests with `pytest`.

### Getting API keys

Step-by-step instructions for creating the Kroger and Walmart.io accounts,
generating the Walmart RSA key, and wiring everything into `.env` are in
[docs/API_SETUP.md](docs/API_SETUP.md).

### Keeping secrets out of this public repo

- Keys are read **only by the backend** from environment variables (`.env` locally,
  your host's secret settings in production). Nothing secret is sent to the browser.
- `.env`, `*.pem` and `*.key` are git-ignored; `.env.example` holds placeholders only.
- `pre-commit` (gitleaks + private-key detector) and the CI `secret-scan` job fail
  if a secret is committed. If one ever leaks, rotate it in the store's portal.

### Architecture

- `backend/main.py`: FastAPI app.
  - `GET /api/stores`: each store with `status` set to `live`, `not_configured`,
    `coming_soon`, or `demo`.
  - `POST /api/search` with body `{"query": "milk", "stores": ["walmart", "kroger"], "zip_code": "45202", "limit": 5}`.
    It queries the stores in parallel and returns `results` (normalized
    products) plus a `stores` list. Each entry in `stores` has a per-store
    `status`/`message`, so a store outage shows up as `error` instead of an
    empty result.
- `backend/store_clients/`
  - `walmart.py`: signs requests (`WM_CONSUMER.ID`, `WM_CONSUMER.INTIMESTAMP`,
    `WM_SEC.KEY_VERSION`, `WM_SEC.AUTH_SIGNATURE`) and maps search results.
  - `kroger.py`: gets an OAuth2 client-credentials token (cached), maps the ZIP
    to the nearest store (cached), and searches products with that store's
    prices.
  - `mock_clients.py`: demo data for UI work, used only with `USE_MOCK_DATA=true`.
- `backend/config.py`: the store registry plus all settings, read from the environment.
- `frontend/`: vanilla JS UI with a ZIP input, per-store status badges, and a comparison basket.

### Configuration

See [.env.example](.env.example) for every variable:

- `KROGER_CLIENT_ID`, `KROGER_CLIENT_SECRET`
- `WALMART_CONSUMER_ID`, `WALMART_KEY_VERSION`, and either
  `WALMART_PRIVATE_KEY_PATH` or `WALMART_PRIVATE_KEY`
- Optional: `WALMART_PUBLISHER_ID`, `DEFAULT_ZIP_CODE`, `USE_MOCK_DATA`,
  `CORS_ALLOW_ORIGINS`, `HTTP_TIMEOUT_SECONDS`, `LOG_LEVEL`
