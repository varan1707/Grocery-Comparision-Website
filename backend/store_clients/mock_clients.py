from __future__ import annotations

import itertools
import random
from typing import List

from backend.config import STORE_DISPLAY_NAMES
from backend.models import StoreProduct
from backend.store_clients.base import BaseStoreClient


class MockStoreClient(BaseStoreClient):
    """Fallback mock implementation.

    This client does NOT hit any external API. It exists to keep the app
    runnable end-to-end while you wire in real store APIs.

    Replace instances of this class with real HTTP-based clients for each
    retailer once you have credentials or scraping adapters ready.
    """

    def __init__(self, store_id: str) -> None:
        self.store_id = store_id
        self.store_name = STORE_DISPLAY_NAMES.get(store_id, store_id.title())

    async def search_products(self, query: str, limit: int = 5) -> List[StoreProduct]:
        base_price = random.uniform(1.0, 10.0)
        step = random.uniform(0.1, 1.0)

        products: List[StoreProduct] = []
        for i in itertools.islice(itertools.count(1), limit):
            price = round(base_price + step * (i - 1), 2)
            products.append(
                StoreProduct(
                    store_id=self.store_id,
                    store_name=self.store_name,
                    product_id=f"{self.store_id}-{i}",
                    name=f"{query.title()} ({self.store_name} option {i})",
                    price=price,
                    unit="per item",
                    image_url=None,
                    product_url=None,
                )
            )
        return products


