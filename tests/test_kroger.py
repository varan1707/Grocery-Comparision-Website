from __future__ import annotations

import asyncio

import httpx
import pytest

from backend.store_clients.base import StoreClientError
from backend.store_clients.kroger import KrogerClient
from tests.fixtures import KROGER_LOCATIONS, KROGER_PRODUCTS, KROGER_TOKEN


class FakeKroger:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if request.url.path.endswith("/connect/oauth2/token"):
            return httpx.Response(200, json=KROGER_TOKEN)
        if request.url.path.endswith("/locations"):
            return httpx.Response(200, json=KROGER_LOCATIONS)
        if request.url.path.endswith("/products"):
            return httpx.Response(200, json=KROGER_PRODUCTS)
        return httpx.Response(404)


def _client(handler, **kwargs) -> KrogerClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return KrogerClient("id", "secret", http, base_url="https://kr.test/v1", **kwargs)


def test_search_uses_token_and_nearest_location():
    fake = FakeKroger()
    client = _client(fake)

    async def run():
        first = await client.search_products("milk", limit=5, zip_code="45202")
        await client.search_products("eggs", limit=5, zip_code="45202")
        return first

    result = asyncio.run(run())

    token_calls = [c for c in fake.calls if c.url.path.endswith("/token")]
    location_calls = [c for c in fake.calls if c.url.path.endswith("/locations")]
    product_calls = [c for c in fake.calls if c.url.path.endswith("/products")]
    assert len(token_calls) == 1, "token should be cached"
    assert len(location_calls) == 1, "ZIP -> location should be cached"
    assert token_calls[0].headers["Authorization"].startswith("Basic ")
    assert b"grant_type=client_credentials" in token_calls[0].content
    assert b"scope=product.compact" in token_calls[0].content
    assert location_calls[0].url.params["filter.zipCode.near"] == "45202"
    assert product_calls[0].url.params["filter.locationId"] == "01400943"
    assert product_calls[0].url.params["filter.term"] == "milk"
    assert product_calls[0].headers["Authorization"] == "Bearer test-token"

    assert result.location == "Kroger - Over-the-Rhine, 1420 Vine St, Cincinnati"
    assert [p.product_id for p in result.products] == ["0001111041700", "0001111041600"]
    promo, regular = result.products
    assert promo.price == 2.99 and promo.regular_price == 3.29
    assert promo.unit == "1 gal"
    assert promo.image_url == "https://www.kroger.com/medium.jpg"
    assert regular.price == 3.49 and regular.regular_price is None


def test_zip_code_required_without_default():
    with pytest.raises(StoreClientError, match="ZIP"):
        asyncio.run(_client(FakeKroger()).search_products("milk"))


def test_default_zip_code_is_used():
    fake = FakeKroger()
    asyncio.run(_client(fake, default_zip_code="45202").search_products("milk"))
    assert any(c.url.path.endswith("/locations") for c in fake.calls)


def test_bad_credentials_reported():
    client = _client(lambda r: httpx.Response(401, json={"error": "invalid_client"}))
    with pytest.raises(StoreClientError, match="credentials"):
        asyncio.run(client.search_products("milk", zip_code="45202"))
