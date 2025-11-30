## Grocery Comparison App (Live Store APIs)

This project is a minimal end-to-end app that compares grocery prices across
major US chains (Walmart, Kroger, Aldi, Whole Foods, Trader Joe's).

**Key design principle:** pricing data is fetched in real time from online
store APIs (or HTTP endpoints you control), *not* from a static database.

### High-level architecture

- **Backend (`backend/`, FastAPI):**
  - `/api/search` – accepts a product search query and selected stores and
    returns normalized product results per store.
  - Store-specific clients (`backend/store_clients/*.py`) encapsulate the logic
    of calling each retailer's API or HTTP endpoint.
  - No database is used for prices; every request results in outbound HTTP
    calls to the configured store endpoints (with a simple mock fallback so the
    app can still run before you wire real APIs).

- **Frontend (`frontend/`, vanilla JS):**
  - Simple single-page UI:
    - Enter an item (e.g., "milk").
    - Select which stores to compare (Walmart, Kroger, Aldi, Whole Foods,
      Trader Joe's).
    - See a table of results and add items to a "comparison list" / basket.
  - All comparisons are done client-side using the live data from the backend.

### Store integration layer

All integrations go through the `BaseStoreClient` interface:

- `backend/store_clients/base.py` defines `BaseStoreClient` with
  `search_products(query: str, limit: int) -> List[StoreProduct]`.
- `backend/models.py` defines the normalized `StoreProduct` returned to the UI.

Concrete implementations:

- `WalmartClient` (`backend/store_clients/walmart.py`)
  - Skeleton that demonstrates how to call a real HTTP API using `httpx`.
  - Reads credentials and base URL from environment variables:
    - `WALMART_API_KEY`
    - `WALMART_BASE_URL`
  - You must plug in the real Walmart endpoint path and response mapping.

- Generic simple HTTP clients (`backend/store_clients/other_stores.py`)
  - `SimpleHttpStoreClient` expects a uniform JSON shape like:

    ```json
    {
      "items": [
        {
          "id": "123",
          "name": "2% Milk Gallon",
          "price": 3.49,
          "currency": "USD",
          "unit": "per gallon",
          "image_url": "https://...",
          "product_url": "https://..."
        }
      ]
    }
    ```

  - Builder helpers:
    - `build_kroger_client()` → `KROGER_BASE_URL`
    - `build_aldi_client()` → `ALDI_BASE_URL`
    - `build_wholefoods_client()` → `WHOLEFOODS_BASE_URL`
    - `build_traderjoes_client()` → `TRADERJOES_BASE_URL`

- Mock fallback (`backend/store_clients/mock_clients.py`)
  - When no base URL / API key is configured, a `MockStoreClient` generates
    reasonable-looking prices so the UI and flows remain testable.
  - This is the only place with fake data; it is deliberately isolated so you
    can delete/replace it once real integrations exist.

### Backend API overview

- `POST /api/search`
  - Body:

    ```json
    {
      "query": "milk",
      "stores": ["walmart", "kroger", "aldi", "wholefoods", "traderjoes"],
      "limit": 5
    }
    ```

  - Response:

    ```json
    {
      "query": "milk",
      "results": [
        {
          "store_id": "walmart",
          "store_name": "Walmart",
          "product_id": "123",
          "name": "2% Milk Gallon",
          "price": 3.49,
          "currency": "USD",
          "unit": "per gallon",
          "image_url": "https://...",
          "product_url": "https://..."
        }
      ]
    }
    ```

- `GET /api/stores`
  - Returns a map of supported store IDs to display names.

### Running the backend

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate  # on Windows PowerShell
pip install -r requirements.txt

uvicorn backend.main:app --reload
```

The API will listen on `http://localhost:8000`.

### Running the frontend

You can open `frontend/index.html` directly in a browser, or serve it with a
simple static server (e.g. VS Code Live Server, `python -m http.server`, etc.).

Ensure the backend is running at `http://localhost:8000` so the UI can call it.

### Wiring real store APIs

1. **Get API access (or scraping adapters)** for each retailer:
   - Use official APIs where available (e.g., developer portals).
   - For stores without public APIs, you may choose to use a third-party
     aggregator API or a compliant scraping service. Keep terms of service and
     legal constraints in mind.

2. **Configure environment variables** (e.g. via a `.env` file):

   ```env
   WALMART_API_KEY=...
   WALMART_BASE_URL=https://api.your-provider.com/walmart
   KROGER_BASE_URL=https://api.your-provider.com/kroger
   ALDI_BASE_URL=https://api.your-provider.com/aldi
   WHOLEFOODS_BASE_URL=https://api.your-provider.com/wholefoods
   TRADERJOES_BASE_URL=https://api.your-provider.com/traderjoes
   LOG_LEVEL=INFO
   ```

3. **Implement the response mapping**:
   - Update `WalmartClient.search_products` with the real JSON keys coming back
     from Walmart (or the intermediary provider you use).
   - Ensure the other stores' endpoints return the expected JSON shape for
     `SimpleHttpStoreClient` or create dedicated clients if needed.

4. **Optionally add caching**:
   - You may layer a short-lived in-memory cache (e.g. 1–5 minutes) around
     outbound calls to reduce latency and API costs, while still keeping data
     effectively real time.

At this point, every user search will fan out to the configured stores, and
the comparison UI will always reflect the latest prices from those platforms,
without relying on any static database.


