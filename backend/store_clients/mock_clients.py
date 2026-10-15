from __future__ import annotations

import itertools
import random
from typing import Optional

from backend.config import STORE_DISPLAY_NAMES
from backend.models import StoreProduct
from backend.store_clients.base import BaseStoreClient, StoreSearchResult


class MockStoreClient(BaseStoreClient):
    """Fake prices for local UI development only.

    Used only when `USE_MOCK_DATA=true`; results are labelled "demo" in the API
    response and the UI so they are never mistaken for real prices.
    """

    def __init__(self, store_id: str) -> None:
        self.store_id = store_id
        self.store_name = STORE_DISPLAY_NAMES.get(store_id, store_id.title())

    async def search_products(
        self, query: str, limit: int = 5, zip_code: Optional[str] = None
    ) -> StoreSearchResult:
        base_price = random.uniform(1.0, 10.0)
        step = random.uniform(0.1, 1.0)

        products = []
        for i in itertools.islice(itertools.count(1), limit):
            products.append(
                StoreProduct(
                    store_id=self.store_id,
                    store_name=self.store_name,
                    product_id=f"{self.store_id}-{i}",
                    name=f"{query.title()} (demo {self.store_name} option {i})",
                    price=round(base_price + step * (i - 1), 2),
                    unit="per item",
                )
            )
        return StoreSearchResult(products=products)
