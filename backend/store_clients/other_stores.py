from __future__ import annotations

from typing import List

import httpx

from backend.config import API_CONFIG, STORE_DISPLAY_NAMES
from backend.models import StoreProduct
from backend.store_clients.base import BaseStoreClient


class SimpleHttpStoreClient(BaseStoreClient):
    """Generic HTTP client using a simple search endpoint.

    This is a convenience implementation you can reuse for Kroger, Aldi,
    Whole Foods, and Trader Joe's if you or a third-party provider expose
    a uniform API shape for them.
    """

    def __init__(self, store_id: str, base_url: str) -> None:
        self.store_id = store_id
        self.store_name = STORE_DISPLAY_NAMES.get(store_id, store_id.title())
        self.base_url = base_url.rstrip("/")

    async def search_products(self, query: str, limit: int = 5) -> List[StoreProduct]:
        if not self.base_url:
            return []

        url = f"{self.base_url}/search"
        params = {"q": query, "limit": limit}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        items_raw = data.get("items") or data.get("products") or []

        products: List[StoreProduct] = []
        for raw in items_raw[:limit]:
            products.append(
                StoreProduct(
                    store_id=self.store_id,
                    store_name=self.store_name,
                    product_id=str(raw.get("id")),
                    name=raw.get("name") or raw.get("title"),
                    price=float(raw.get("price")),
                    currency=raw.get("currency") or "USD",
                    unit=raw.get("unit"),
                    image_url=raw.get("image_url"),
                    product_url=raw.get("product_url"),
                )
            )

        return products


def build_kroger_client() -> BaseStoreClient | None:
    if not API_CONFIG.kroger_base_url:
        return None
    return SimpleHttpStoreClient("kroger", API_CONFIG.kroger_base_url)


def build_aldi_client() -> BaseStoreClient | None:
    if not API_CONFIG.aldi_base_url:
        return None
    return SimpleHttpStoreClient("aldi", API_CONFIG.aldi_base_url)


def build_wholefoods_client() -> BaseStoreClient | None:
    if not API_CONFIG.wholefoods_base_url:
        return None
    return SimpleHttpStoreClient("wholefoods", API_CONFIG.wholefoods_base_url)


def build_traderjoes_client() -> BaseStoreClient | None:
    if not API_CONFIG.traderjoes_base_url:
        return None
    return SimpleHttpStoreClient("traderjoes", API_CONFIG.traderjoes_base_url)


