from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StoreProduct(BaseModel):
    store_id: str = Field(..., description="Internal store identifier, e.g. 'walmart'")
    store_name: str = Field(..., description="Human readable store name")
    product_id: str = Field(..., description="Store-specific product identifier")
    name: str
    price: float
    currency: str = "USD"
    unit: Optional[str] = Field(
        default=None, description="e.g. 'per lb', 'per item', 'per oz'"
    )
    image_url: Optional[str] = None
    product_url: Optional[str] = None


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search term for the product")
    stores: List[str] = Field(
        default_factory=list,
        description="List of store ids to search, e.g. ['walmart', 'aldi']",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max number of products per store to return",
    )


class SearchResponse(BaseModel):
    query: str
    results: List[StoreProduct]


