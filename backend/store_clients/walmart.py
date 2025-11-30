from __future__ import annotations

from typing import List

import httpx

from backend.config import API_CONFIG
from backend.models import StoreProduct
from backend.store_clients.base import BaseStoreClient


class WalmartClient(BaseStoreClient):
    """Example of how to wire a real HTTP-based client.

    IMPORTANT: This is a skeleton. You must plug in the actual Walmart
    product search endpoint and authentication scheme. The key idea is that
    data is fetched live from Walmart's online systems, not from our own DB.
    """

    store_id = "walmart"
    store_name = "Walmart"

    async def search_products(self, query: str, limit: int = 5) -> List[StoreProduct]:
        if not API_CONFIG.walmart_base_url or not API_CONFIG.walmart_api_key:
            # Fallback to empty list if not configured; the app still runs.
            return []

        # NOTE: Replace the URL path and parameter names with the real API.
        url = f"{API_CONFIG.walmart_base_url.rstrip('/')}/search"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {API_CONFIG.walmart_api_key}",
        }
        params = {"q": query, "limit": limit}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        # The exact mapping depends on the real response format.
        items_raw = data.get("items") or data.get("products") or []

        products: List[StoreProduct] = []
        for raw in items_raw[:limit]:
            products.append(
                StoreProduct(
                    store_id=self.store_id,
                    store_name=self.store_name,
                    product_id=str(raw.get("id") or raw.get("itemId")),
                    name=raw.get("name") or raw.get("title") or query,
                    price=float(raw.get("price") or raw.get("salePrice") or 0.0),
                    currency=raw.get("currency") or "USD",
                    unit=None,
                    image_url=raw.get("image") or raw.get("imageUrl"),
                    product_url=raw.get("productUrl") or raw.get("product_url"),
                )
            )

        return products


