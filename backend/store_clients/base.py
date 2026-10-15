from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Optional

from backend.models import StoreProduct


class StoreClientError(Exception):
    """A store request failed; the message is safe to show to end users."""


@dataclass
class StoreSearchResult:
    products: List[StoreProduct] = field(default_factory=list)
    location: Optional[str] = None


class BaseStoreClient(abc.ABC):
    """Abstract interface for all grocery store clients.

    Each concrete implementation translates our normalized `query` into the
    respective store API call and maps the response back into `StoreProduct`
    objects.
    """

    store_id: str
    store_name: str

    @abc.abstractmethod
    async def search_products(
        self, query: str, limit: int = 5, zip_code: Optional[str] = None
    ) -> StoreSearchResult:
        """Search products for the given query."""
