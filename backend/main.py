from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import (
    STORE_DISPLAY_NAMES,
    STORE_IDS,
    API_CONFIG,
    configure_logging,
)
from backend.models import SearchQuery, SearchResponse, StoreProduct
from backend.store_clients.base import BaseStoreClient
from backend.store_clients.mock_clients import MockStoreClient
from backend.store_clients.other_stores import (
    build_aldi_client,
    build_kroger_client,
    build_traderjoes_client,
    build_wholefoods_client,
)
from backend.store_clients.walmart import WalmartClient


BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Grocery Price Comparison API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def build_store_clients() -> Dict[str, BaseStoreClient]:
    """Instantiate clients for all supported stores.

    For now, only Walmart has an explicit HTTP-based client skeleton.
    Others use `SimpleHttpStoreClient` if base URLs are configured.
    Any missing store falls back to a mock client, so the app always runs.
    """
    clients: Dict[str, BaseStoreClient] = {}

    # Walmart
    walmart_client: BaseStoreClient
    if API_CONFIG.walmart_base_url and API_CONFIG.walmart_api_key:
        walmart_client = WalmartClient()
    else:
        walmart_client = MockStoreClient("walmart")
    clients["walmart"] = walmart_client

    # Kroger, Aldi, Whole Foods, Trader Joe's via SimpleHttpStoreClient
    kroger = build_kroger_client() or MockStoreClient("kroger")
    aldi = build_aldi_client() or MockStoreClient("aldi")
    wholefoods = build_wholefoods_client() or MockStoreClient("wholefoods")
    traderjoes = build_traderjoes_client() or MockStoreClient("traderjoes")

    clients["kroger"] = kroger
    clients["aldi"] = aldi
    clients["wholefoods"] = wholefoods
    clients["traderjoes"] = traderjoes

    return clients


STORE_CLIENTS: Dict[str, BaseStoreClient] = build_store_clients()


@app.get("/")
async def serve_frontend() -> FileResponse:
    """Serve the main frontend HTML at the root path."""
    if not INDEX_FILE.exists():
        logger.error("Frontend index.html not found at %s", INDEX_FILE)
        raise HTTPException(status_code=500, detail="Frontend not available.")
    return FileResponse(INDEX_FILE)


@app.get("/api/stores", response_model=Dict[str, str])
async def list_stores() -> Dict[str, str]:
    """Return supported store IDs and display names."""
    return STORE_DISPLAY_NAMES


@app.post("/api/search", response_model=SearchResponse)
async def search_products(body: SearchQuery) -> SearchResponse:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    stores: List[str] = body.stores or STORE_IDS
    invalid_stores = [s for s in stores if s not in STORE_CLIENTS]
    if invalid_stores:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown store ids requested: {', '.join(invalid_stores)}",
        )

    all_results: List[StoreProduct] = []

    for store_id in stores:
        client = STORE_CLIENTS[store_id]
        try:
            results = await client.search_products(body.query, limit=body.limit)
            all_results.extend(results)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Store client failed for %s: %s", store_id, exc)

    return SearchResponse(query=body.query, results=all_results)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


