from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from backend.config import ApiConfig
from backend.main import create_app
from tests.fixtures import KROGER_LOCATIONS, KROGER_PRODUCTS, KROGER_TOKEN


def _config(**overrides) -> ApiConfig:
    base = dict(
        kroger_client_id=None,
        kroger_client_secret=None,
        walmart_consumer_id=None,
        walmart_private_key=None,
        default_zip_code=None,
        use_mock_data=False,
    )
    base.update(overrides)
    return ApiConfig(**base)


def _kroger_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/token"):
        return httpx.Response(200, json=KROGER_TOKEN)
    if request.url.path.endswith("/locations"):
        return httpx.Response(200, json=KROGER_LOCATIONS)
    return httpx.Response(200, json=KROGER_PRODUCTS)


def test_stores_report_status_without_credentials():
    with TestClient(create_app(_config())) as client:
        stores = {s["store_id"]: s["status"] for s in client.get("/api/stores").json()}
    assert stores == {
        "walmart": "not_configured",
        "kroger": "not_configured",
        "target": "coming_soon",
        "aldi": "coming_soon",
        "wholefoods": "coming_soon",
        "traderjoes": "coming_soon",
    }


def test_search_never_returns_fake_prices_by_default():
    with TestClient(create_app(_config())) as client:
        body = client.post("/api/search", json={"query": "milk"}).json()
    assert body["results"] == []
    assert {s["status"] for s in body["stores"]} == {"not_configured", "coming_soon"}


def test_search_with_live_kroger(rsa_key_pem):
    http = httpx.AsyncClient(transport=httpx.MockTransport(_kroger_handler))
    config = _config(kroger_client_id="id", kroger_client_secret="secret")
    with TestClient(create_app(config, http=http)) as client:
        resp = client.post(
            "/api/search",
            json={"query": "milk", "stores": ["kroger", "target"], "zip_code": "45202"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 2
    statuses = {s["store_id"]: s for s in body["stores"]}
    assert statuses["kroger"]["status"] == "live"
    assert statuses["kroger"]["result_count"] == 2
    assert statuses["target"]["status"] == "coming_soon"


def test_store_errors_are_surfaced_not_swallowed(rsa_key_pem):
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    http = httpx.AsyncClient(transport=httpx.MockTransport(failing))
    config = _config(walmart_consumer_id="c", walmart_private_key=rsa_key_pem)
    with TestClient(create_app(config, http=http)) as client:
        body = client.post("/api/search", json={"query": "milk", "stores": ["walmart"]}).json()
    assert body["results"] == []
    assert body["stores"][0]["status"] == "error"
    assert "unavailable" in body["stores"][0]["message"]


def test_mock_data_is_opt_in_and_labelled():
    with TestClient(create_app(_config(use_mock_data=True))) as client:
        body = client.post("/api/search", json={"query": "milk", "stores": ["walmart"]}).json()
    assert body["stores"][0]["status"] == "demo"
    assert len(body["results"]) == 5


def test_invalid_zip_and_unknown_store_rejected():
    with TestClient(create_app(_config())) as client:
        assert client.post("/api/search", json={"query": "milk", "zip_code": "abc"}).status_code == 422
        assert client.post("/api/search", json={"query": "milk", "stores": ["costco"]}).status_code == 400
