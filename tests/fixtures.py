"""Trimmed sample payloads shaped like the official API responses."""

WALMART_SEARCH = {
    "query": "milk",
    "totalResults": 2,
    "start": 1,
    "numItems": 3,
    "items": [
        {
            "itemId": 10450114,
            "name": "Great Value Whole Milk, 1 Gallon",
            "msrp": 3.98,
            "salePrice": 3.48,
            "size": "128 fl oz",
            "thumbnailImage": "https://i5.walmartimages.com/thumb.jpeg",
            "mediumImage": "https://i5.walmartimages.com/medium.jpeg",
            "productTrackingUrl": "https://goto.walmart.com/c/|PUBID|/568844/9383?prodsku=10450114",
        },
        {
            "itemId": 10450115,
            "name": "Great Value 2% Milk, 1 Gallon",
            "bestMarketplacePrice": {"price": 3.28},
            "productUrl": "https://www.walmart.com/ip/10450115",
        },
        {"itemId": 999, "name": "No price item"},
    ],
}

KROGER_TOKEN = {"access_token": "test-token", "expires_in": 1800, "token_type": "bearer"}

KROGER_LOCATIONS = {
    "data": [
        {
            "locationId": "01400943",
            "chain": "KROGER",
            "name": "Kroger - Over-the-Rhine",
            "address": {"addressLine1": "1420 Vine St", "city": "Cincinnati", "zipCode": "45202"},
        }
    ]
}

KROGER_PRODUCTS = {
    "data": [
        {
            "productId": "0001111041700",
            "description": "Kroger 2% Reduced Fat Milk",
            "brand": "Kroger",
            "images": [
                {
                    "perspective": "front",
                    "featured": True,
                    "sizes": [
                        {"size": "large", "url": "https://www.kroger.com/large.jpg"},
                        {"size": "medium", "url": "https://www.kroger.com/medium.jpg"},
                    ],
                }
            ],
            "items": [{"itemId": "0001111041700", "price": {"regular": 3.29, "promo": 2.99}, "size": "1 gal"}],
        },
        {
            "productId": "0001111041600",
            "description": "Kroger Whole Milk",
            "items": [{"itemId": "0001111041600", "price": {"regular": 3.49, "promo": 0}, "size": "1 gal"}],
        },
        {
            "productId": "0001111099999",
            "description": "Unpriced at this store",
            "items": [{"itemId": "0001111099999"}],
        },
    ]
}
