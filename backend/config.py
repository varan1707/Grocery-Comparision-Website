from __future__ import annotations

import logging
import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def configure_logging() -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


STORE_IDS: List[str] = ["walmart", "kroger", "aldi", "wholefoods", "traderjoes"]

STORE_DISPLAY_NAMES: Dict[str, str] = {
    "walmart": "Walmart",
    "kroger": "Kroger",
    "aldi": "Aldi",
    "wholefoods": "Whole Foods",
    "traderjoes": "Trader Joe's",
}


class ApiConfig:
    """Configuration for external store APIs.

    In a real deployment, populate these from environment variables or a vault
    with the actual API keys / hosts for each retailer.
    """

    walmart_api_key: str | None = os.getenv("WALMART_API_KEY")
    walmart_base_url: str | None = os.getenv("WALMART_BASE_URL")

    kroger_api_key: str | None = os.getenv("KROGER_API_KEY")
    kroger_base_url: str | None = os.getenv("KROGER_BASE_URL")

    aldi_base_url: str | None = os.getenv("ALDI_BASE_URL")

    wholefoods_base_url: str | None = os.getenv("WHOLEFOODS_BASE_URL")

    traderjoes_base_url: str | None = os.getenv("TRADERJOES_BASE_URL")


API_CONFIG = ApiConfig()


