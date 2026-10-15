from __future__ import annotations

import asyncio
import time
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend.models import StoreProduct
from backend.store_clients.base import (
    BaseStoreClient,
    StoreClientError,
    StoreSearchResult,
)

TOKEN_SCOPE = "product.compact"


class KrogerClient(BaseStoreClient):
    """Kroger Public API (https://developer.kroger.com).

    Auth: OAuth2 client-credentials (client id + secret -> bearer token).
    Prices are only returned when a `filter.locationId` is supplied, so the
    user's ZIP code is first resolved to the nearest Kroger-family store.
    """

    store_id = "kroger"
    store_name = "Kroger"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        http: httpx.AsyncClient,
        base_url: str = "https://api.kroger.com/v1",
        default_zip_code: Optional[str] = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._default_zip_code = default_zip_code
        self._token: Optional[str] = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self._locations: Dict[str, Tuple[str, str]] = {}

    async def _get_token(self) -> str:
        async with self._token_lock:
            if self._token and time.monotonic() < self._token_expires_at - 60:
                return self._token
            resp = await self._http.post(
                f"{self._base_url}/connect/oauth2/token",
                data={"grant_type": "client_credentials", "scope": TOKEN_SCOPE},
                auth=(self._client_id, self._client_secret),
            )
            if resp.status_code in (400, 401):
                raise StoreClientError(
                    "Kroger rejected the API credentials (check KROGER_CLIENT_ID/SECRET)."
                )
            resp.raise_for_status()
            payload = resp.json()
            self._token = payload["access_token"]
            self._token_expires_at = time.monotonic() + float(
                payload.get("expires_in", 1800)
            )
            return self._token

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        token = await self._get_token()
        resp = await self._http.get(
            f"{self._base_url}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        if resp.status_code == 401:
            self._token = None
            raise StoreClientError("Kroger API token was rejected; try again.")
        if resp.status_code == 429:
            raise StoreClientError("Kroger API rate limit reached; try again later.")
        resp.raise_for_status()
        return resp.json()

    async def _resolve_location(self, zip_code: str) -> Tuple[str, str]:
        if zip_code in self._locations:
            return self._locations[zip_code]
        data = await self._get(
            "/locations",
            {"filter.zipCode.near": zip_code, "filter.limit": 1},
        )
        locations = data.get("data") or []
        if not locations:
            raise StoreClientError(f"No Kroger-family store found near {zip_code}.")
        loc = locations[0]
        address = loc.get("address") or {}
        label = ", ".join(
            part
            for part in (
                loc.get("name"),
                address.get("addressLine1"),
                address.get("city"),
            )
            if part
        )
        resolved = (str(loc["locationId"]), label or str(loc["locationId"]))
        self._locations[zip_code] = resolved
        return resolved

    async def search_products(
        self, query: str, limit: int = 5, zip_code: Optional[str] = None
    ) -> StoreSearchResult:
        zip_code = zip_code or self._default_zip_code
        if not zip_code:
            raise StoreClientError("Enter a ZIP code to see Kroger prices.")

        location_id, location_label = await self._resolve_location(zip_code)
        # Ask for extra items because some come back without a price at this store.
        data = await self._get(
            "/products",
            {
                "filter.term": query,
                "filter.locationId": location_id,
                "filter.limit": min(limit * 2, 50),
            },
        )
        products = parse_products(data, self.store_id, self.store_name)[:limit]
        return StoreSearchResult(products=products, location=location_label)


def _pick_image(images: List[Dict[str, Any]]) -> Optional[str]:
    if not images:
        return None
    image = next((i for i in images if i.get("featured")), images[0])
    sizes = image.get("sizes") or []
    by_size = {s.get("size"): s.get("url") for s in sizes}
    for preferred in ("medium", "small", "large", "thumbnail", "xlarge"):
        if by_size.get(preferred):
            return by_size[preferred]
    return sizes[0].get("url") if sizes else None


def parse_products(
    data: Dict[str, Any], store_id: str, store_name: str
) -> List[StoreProduct]:
    products: List[StoreProduct] = []
    for raw in data.get("data") or []:
        items = raw.get("items") or []
        item = items[0] if items else {}
        price_info = item.get("price") or {}
        regular = price_info.get("regular")
        promo = price_info.get("promo")
        price = promo if promo else regular
        if not price or not raw.get("productId") or not raw.get("description"):
            continue
        product_id = str(raw["productId"])
        slug = raw.get("productPageURI")
        products.append(
            StoreProduct(
                store_id=store_id,
                store_name=store_name,
                product_id=product_id,
                name=raw["description"],
                price=float(price),
                regular_price=float(regular) if promo and regular else None,
                unit=item.get("size") or None,
                image_url=_pick_image(raw.get("images") or []),
                product_url=(
                    f"https://www.kroger.com{slug}"
                    if slug
                    else f"https://www.kroger.com/search?query={quote(raw['description'])}"
                ),
            )
        )
    return products
