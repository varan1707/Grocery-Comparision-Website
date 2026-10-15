from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import API_CONFIG, STORE_IDS, STORES, STORES_BY_ID, ApiConfig, configure_logging
from backend.models import (
    SearchQuery,
    SearchResponse,
    StoreInfo,
    StoreProduct,
    StoreSearchStatus,
)
from backend.store_clients.base import BaseStoreClient, StoreClientError
from backend.store_clients.kroger import KrogerClient
from backend.store_clients.mock_clients import MockStoreClient
from backend.store_clients.walmart import WalmartClient

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"

configure_logging()
logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE = {
    "walmart": "Walmart API keys not set (WALMART_CONSUMER_ID / WALMART_PRIVATE_KEY).",
    "kroger": "Kroger API keys not set (KROGER_CLIENT_ID / KROGER_CLIENT_SECRET).",
}


def build_store_clients(config: ApiConfig, http: httpx.AsyncClient) -> Dict[str, BaseStoreClient]:
    """Create a client for every store that has credentials configured.

    Stores without credentials are left out (reported as `not_configured`),
    unless USE_MOCK_DATA is on, in which case they get clearly-labelled demo data.
    """
    clients: Dict[str, BaseStoreClient] = {}

    if config.walmart_configured:
        try:
            clients["walmart"] = WalmartClient(
                consumer_id=config.walmart_consumer_id,  # type: ignore[arg-type]
                private_key=config.walmart_private_key,  # type: ignore[arg-type]
                http=http,
                key_version=config.walmart_key_version,
                publisher_id=config.walmart_publisher_id,
                base_url=config.walmart_base_url,
            )
        except ValueError:
            logger.error("WALMART_PRIVATE_KEY could not be loaded as a PKCS#8 RSA key")

    if config.kroger_configured:
        clients["kroger"] = KrogerClient(
            client_id=config.kroger_client_id,  # type: ignore[arg-type]
            client_secret=config.kroger_client_secret,  # type: ignore[arg-type]
            http=http,
            base_url=config.kroger_base_url,
            default_zip_code=config.default_zip_code,
        )

    if config.use_mock_data:
        for store in STORES:
            if store.integration != "coming_soon" and store.store_id not in clients:
                clients[store.store_id] = MockStoreClient(store.store_id)

    for store in STORES:
        if store.integration == "coming_soon":
            continue
        if store.store_id in clients:
            mode = "demo" if isinstance(clients[store.store_id], MockStoreClient) else "live"
            logger.info("Store %s: %s", store.store_id, mode)
        else:
            logger.warning("Store %s: not configured", store.store_id)

    return clients


def store_info(store_id: str, clients: Dict[str, BaseStoreClient]) -> StoreInfo:
    store = STORES_BY_ID[store_id]
    if store.integration == "coming_soon":
        return StoreInfo(
            store_id=store_id,
            store_name=store.display_name,
            status="coming_soon",
            message=f"Prices coming soon. {store.note}".strip(),
        )
    client = clients.get(store_id)
    if client is None:
        return StoreInfo(
            store_id=store_id,
            store_name=store.display_name,
            status="not_configured",
            message=NOT_CONFIGURED_MESSAGE.get(store_id),
        )
    if isinstance(client, MockStoreClient):
        return StoreInfo(
            store_id=store_id,
            store_name=store.display_name,
            status="demo",
            message="Demo data (USE_MOCK_DATA=true), not real prices.",
        )
    return StoreInfo(store_id=store_id, store_name=store.display_name, status="live")


async def search_store(
    store_id: str,
    clients: Dict[str, BaseStoreClient],
    query: str,
    limit: int,
    zip_code: Optional[str],
) -> tuple[StoreSearchStatus, List[StoreProduct]]:
    info = store_info(store_id, clients)
    status = StoreSearchStatus(**info.model_dump())
    client = clients.get(store_id)
    if client is None or info.status == "coming_soon":
        return status, []
    try:
        result = await client.search_products(query, limit=limit, zip_code=zip_code)
    except StoreClientError as exc:
        logger.warning("Store %s: %s", store_id, exc)
        status.status, status.message = "error", str(exc)
        return status, []
    except httpx.TimeoutException:
        logger.warning("Store %s timed out", store_id)
        status.status, status.message = "error", f"{info.store_name} did not respond in time."
        return status, []
    except Exception:  # noqa: BLE001
        logger.exception("Store client failed for %s", store_id)
        status.status, status.message = "error", f"{info.store_name} is unavailable right now."
        return status, []
    status.result_count = len(result.products)
    status.location = result.location
    return status, result.products


def create_app(config: ApiConfig = API_CONFIG, http: Optional[httpx.AsyncClient] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = http or httpx.AsyncClient(timeout=config.http_timeout_seconds)
        app.state.clients = build_store_clients(config, client)
        try:
            yield
        finally:
            if http is None:
                await client.aclose()

    app = FastAPI(title="Grocery Price Comparison API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allow_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        """Serve the main frontend HTML at the root path."""
        if not INDEX_FILE.exists():
            logger.error("Frontend index.html not found at %s", INDEX_FILE)
            raise HTTPException(status_code=500, detail="Frontend not available.")
        return FileResponse(INDEX_FILE)

    @app.get("/api/stores", response_model=List[StoreInfo])
    async def list_stores() -> List[StoreInfo]:
        """Return every store with whether live prices are available for it."""
        return [store_info(s.store_id, app.state.clients) for s in STORES]

    @app.post("/api/search", response_model=SearchResponse)
    async def search_products(body: SearchQuery) -> SearchResponse:
        query = body.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query must not be empty.")

        stores: List[str] = body.stores or STORE_IDS
        invalid_stores = [s for s in stores if s not in STORES_BY_ID]
        if invalid_stores:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown store ids requested: {', '.join(invalid_stores)}",
            )

        outcomes = await asyncio.gather(
            *(
                search_store(s, app.state.clients, query, body.limit, body.zip_code)
                for s in stores
            )
        )
        return SearchResponse(
            query=query,
            results=[p for _, products in outcomes for p in products],
            stores=[status for status, _ in outcomes],
        )

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
