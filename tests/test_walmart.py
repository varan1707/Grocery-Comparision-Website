from __future__ import annotations

import asyncio
import base64

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from backend.store_clients.base import StoreClientError
from backend.store_clients.walmart import WalmartClient, build_auth_headers, load_private_key
from tests.fixtures import WALMART_SEARCH


def test_signature_covers_sorted_header_values(rsa_key):
    headers = build_auth_headers("consumer-123", "1", rsa_key, timestamp_ms=1700000000000)

    assert headers["WM_CONSUMER.ID"] == "consumer-123"
    assert headers["WM_CONSUMER.INTIMESTAMP"] == "1700000000000"
    assert headers["WM_SEC.KEY_VERSION"] == "1"
    rsa_key.public_key().verify(
        base64.b64decode(headers["WM_SEC.AUTH_SIGNATURE"]),
        b"consumer-123\n1700000000000\n1\n",
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def test_load_private_key_accepts_bare_base64_body(rsa_key_pem):
    body = "".join(rsa_key_pem.strip().splitlines()[1:-1])
    assert load_private_key(body).key_size == 2048


def _client(rsa_key_pem, handler) -> WalmartClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WalmartClient("consumer-123", rsa_key_pem, http, base_url="https://wm.test/v2")


def test_search_maps_items_and_sends_auth_headers(rsa_key_pem):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json=WALMART_SEARCH)

    result = asyncio.run(_client(rsa_key_pem, handler).search_products("milk", limit=5))

    req = seen["request"]
    assert req.url.path == "/v2/search"
    assert req.url.params["query"] == "milk"
    assert req.url.params["numItems"] == "5"
    assert "WM_SEC.AUTH_SIGNATURE" in req.headers
    assert [p.product_id for p in result.products] == ["10450114", "10450115"]

    first, second = result.products
    assert first.price == 3.48 and first.regular_price == 3.98
    assert first.unit == "128 fl oz"
    assert first.image_url == "https://i5.walmartimages.com/medium.jpeg"
    assert first.product_url == "https://www.walmart.com/ip/10450114"
    assert second.price == 3.28 and second.regular_price is None
    assert second.product_url == "https://www.walmart.com/ip/10450115"


def test_auth_failure_is_reported(rsa_key_pem):
    client = _client(rsa_key_pem, lambda r: httpx.Response(401, json={}))
    with pytest.raises(StoreClientError, match="credentials"):
        asyncio.run(client.search_products("milk"))
