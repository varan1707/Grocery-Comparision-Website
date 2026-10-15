from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

StoreStatusValue = Literal["live", "demo", "not_configured", "coming_soon", "error"]


class StoreProduct(BaseModel):
    store_id: str = Field(..., description="Internal store identifier, e.g. 'walmart'")
    store_name: str = Field(..., description="Human readable store name")
    product_id: str = Field(..., description="Store-specific product identifier")
    name: str
    price: float
    regular_price: Optional[float] = Field(
        default=None, description="Pre-discount price when the item is on promotion"
    )
    currency: str = "USD"
    unit: Optional[str] = Field(
        default=None, description="e.g. '1 gal', 'per lb', '12 ct'"
    )
    image_url: Optional[str] = None
    product_url: Optional[str] = None


class StoreInfo(BaseModel):
    store_id: str
    store_name: str
    status: StoreStatusValue
    message: Optional[str] = None


class StoreSearchStatus(StoreInfo):
    result_count: int = 0
    location: Optional[str] = Field(
        default=None, description="Store location used for pricing, if any"
    )


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search term for the product")
    stores: List[str] = Field(
        default_factory=list,
        description="List of store ids to search, e.g. ['walmart', 'kroger']",
    )
    zip_code: Optional[str] = Field(
        default=None,
        pattern=r"^\d{5}$",
        description="US ZIP code used to pick a nearby store for location-based prices",
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
    stores: List[StoreSearchStatus]
