from __future__ import annotations

import abc
from typing import List

from backend.models import StoreProduct


class BaseStoreClient(abc.ABC):
    """Abstract interface for all grocery store clients.

    Each concrete implementation should translate our normalized `query`
    into the respective store API (or website) call and map the response
    back into `StoreProduct` objects.
    """

    store_id: str
    store_name: str

    @abc.abstractmethod
    async def search_products(self, query: str, limit: int = 5) -> List[StoreProduct]:
        """Search products for the given query."""


