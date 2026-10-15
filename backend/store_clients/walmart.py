from __future__ import annotations

import base64
import time
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from backend.models import StoreProduct
from backend.store_clients.base import (
    BaseStoreClient,
    StoreClientError,
    StoreSearchResult,
)

def load_private_key(key_text: str) -> rsa.RSAPrivateKey:
    """Load a PKCS#8 RSA key given as PEM or as the bare base64 body."""
    text = key_text.strip()
    if "-----BEGIN" not in text:
        body = "".join(text.split())
        label = "PRIVATE " + "KEY"
        text = f"-----BEGIN {label}-----\n{body}\n-----END {label}-----"
    key = serialization.load_pem_private_key(text.encode(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Walmart private key must be an RSA key")
    return key


def build_auth_headers(
    consumer_id: str,
    key_version: str,
    private_key: rsa.RSAPrivateKey,
    timestamp_ms: Optional[int] = None,
) -> Dict[str, str]:
    """Walmart.io "Additional Headers": SHA256withRSA over the sorted header values.

    See https://walmart.io/docs/affiliates/v1/additional-headers. Signatures
    expire after 180 seconds, so they are generated per request.
    """
    timestamp = str(timestamp_ms if timestamp_ms is not None else int(time.time() * 1000))
    to_sign = {
        "WM_CONSUMER.ID": consumer_id,
        "WM_CONSUMER.INTIMESTAMP": timestamp,
        "WM_SEC.KEY_VERSION": key_version,
    }
    canonical = "".join(f"{to_sign[k].strip()}\n" for k in sorted(to_sign))
    signature = private_key.sign(canonical.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return {
        **to_sign,
        "WM_SEC.AUTH_SIGNATURE": base64.b64encode(signature).decode("ascii"),
    }


class WalmartClient(BaseStoreClient):
    """Walmart.io Affiliate Marketing API product search.

    Returns Walmart.com online prices (the API is not store-specific).
    """

    store_id = "walmart"
    store_name = "Walmart"

    def __init__(
        self,
        consumer_id: str,
        private_key: str,
        http: httpx.AsyncClient,
        key_version: str = "1",
        publisher_id: Optional[str] = None,
        base_url: str = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2",
    ) -> None:
        self._consumer_id = consumer_id
        self._private_key = load_private_key(private_key)
        self._key_version = key_version
        self._publisher_id = publisher_id
        self._http = http
        self._base_url = base_url.rstrip("/")

    async def search_products(
        self, query: str, limit: int = 5, zip_code: Optional[str] = None
    ) -> StoreSearchResult:
        params: Dict[str, Any] = {"query": query, "numItems": min(limit, 25)}
        if self._publisher_id:
            params["publisherId"] = self._publisher_id

        headers = {
            "Accept": "application/json",
            **build_auth_headers(self._consumer_id, self._key_version, self._private_key),
        }
        resp = await self._http.get(f"{self._base_url}/search", params=params, headers=headers)
        if resp.status_code in (401, 403):
            raise StoreClientError(
                "Walmart rejected the API credentials (check WALMART_CONSUMER_ID, "
                "key version and private key)."
            )
        if resp.status_code == 429:
            raise StoreClientError("Walmart API rate limit reached; try again later.")
        resp.raise_for_status()

        products = parse_search_response(resp.json(), self.store_id, self.store_name)
        return StoreSearchResult(products=products[:limit], location="Walmart.com (online)")


def _product_url(raw: Dict[str, Any], item_id: str) -> str:
    tracking = raw.get("productTrackingUrl")
    # Without a publisher id the tracking link still contains the |PUBID| placeholder.
    if tracking and "|PUBID|" not in tracking:
        return tracking
    return raw.get("productUrl") or f"https://www.walmart.com/ip/{item_id}"


def parse_search_response(
    data: Dict[str, Any], store_id: str, store_name: str
) -> List[StoreProduct]:
    products: List[StoreProduct] = []
    for raw in data.get("items") or []:
        price = raw.get("salePrice")
        if price is None and isinstance(raw.get("bestMarketplacePrice"), dict):
            price = raw["bestMarketplacePrice"].get("price")
        if not price or not raw.get("itemId") or not raw.get("name"):
            continue
        msrp = raw.get("msrp")
        item_id = str(raw["itemId"])
        products.append(
            StoreProduct(
                store_id=store_id,
                store_name=store_name,
                product_id=item_id,
                name=raw["name"],
                price=float(price),
                regular_price=float(msrp) if msrp and float(msrp) > float(price) else None,
                unit=raw.get("size") or None,
                image_url=raw.get("mediumImage") or raw.get("thumbnailImage"),
                product_url=_product_url(raw, item_id),
            )
        )
    return products
