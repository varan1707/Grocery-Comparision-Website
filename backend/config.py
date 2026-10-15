from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal

from dotenv import load_dotenv

load_dotenv()


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def configure_logging() -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


Integration = Literal["kroger", "walmart", "coming_soon"]


@dataclass(frozen=True)
class StoreDefinition:
    store_id: str
    display_name: str
    integration: Integration
    note: str = ""


STORES: List[StoreDefinition] = [
    StoreDefinition("walmart", "Walmart", "walmart"),
    StoreDefinition("kroger", "Kroger", "kroger"),
    StoreDefinition(
        "target", "Target", "coming_soon", "No free official product API yet."
    ),
    StoreDefinition(
        "aldi", "Aldi", "coming_soon", "No free official product API yet."
    ),
    StoreDefinition(
        "wholefoods", "Whole Foods", "coming_soon", "No free official product API yet."
    ),
    StoreDefinition(
        "traderjoes", "Trader Joe's", "coming_soon", "No free official product API yet."
    ),
]

STORE_IDS: List[str] = [s.store_id for s in STORES]
STORE_DISPLAY_NAMES: Dict[str, str] = {s.store_id: s.display_name for s in STORES}
STORES_BY_ID: Dict[str, StoreDefinition] = {s.store_id: s for s in STORES}


def _env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _env_bool(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_walmart_private_key() -> str | None:
    """Read the Walmart.io RSA private key from an env var or a file path.

    The key must never be committed: keep it in `.env` (git-ignored) or in a
    file outside the repo referenced by `WALMART_PRIVATE_KEY_PATH`.
    """
    inline = _env("WALMART_PRIVATE_KEY")
    if inline:
        return inline.replace("\\n", "\n")
    path = _env("WALMART_PRIVATE_KEY_PATH")
    if path:
        key_file = Path(path).expanduser()
        if key_file.is_file():
            return key_file.read_text()
        logging.getLogger(__name__).warning(
            "WALMART_PRIVATE_KEY_PATH is set but %s does not exist", key_file
        )
    return None


@dataclass
class ApiConfig:
    """Credentials and endpoints for the store APIs, read from the environment."""

    kroger_client_id: str | None = field(default_factory=lambda: _env("KROGER_CLIENT_ID"))
    kroger_client_secret: str | None = field(
        default_factory=lambda: _env("KROGER_CLIENT_SECRET")
    )
    kroger_base_url: str = field(
        default_factory=lambda: _env("KROGER_BASE_URL") or "https://api.kroger.com/v1"
    )

    walmart_consumer_id: str | None = field(
        default_factory=lambda: _env("WALMART_CONSUMER_ID")
    )
    walmart_private_key: str | None = field(default_factory=_load_walmart_private_key)
    walmart_key_version: str = field(
        default_factory=lambda: _env("WALMART_KEY_VERSION") or "1"
    )
    walmart_publisher_id: str | None = field(
        default_factory=lambda: _env("WALMART_PUBLISHER_ID")
    )
    walmart_base_url: str = field(
        default_factory=lambda: _env("WALMART_BASE_URL")
        or "https://developer.api.walmart.com/api-proxy/service/affil/product/v2"
    )

    default_zip_code: str | None = field(default_factory=lambda: _env("DEFAULT_ZIP_CODE"))
    use_mock_data: bool = field(default_factory=lambda: _env_bool("USE_MOCK_DATA"))
    http_timeout_seconds: float = field(
        default_factory=lambda: float(_env("HTTP_TIMEOUT_SECONDS") or 8.0)
    )
    cors_allow_origins: List[str] = field(
        default_factory=lambda: [
            o.strip() for o in (os.getenv("CORS_ALLOW_ORIGINS") or "*").split(",") if o.strip()
        ]
    )

    @property
    def kroger_configured(self) -> bool:
        return bool(self.kroger_client_id and self.kroger_client_secret)

    @property
    def walmart_configured(self) -> bool:
        return bool(self.walmart_consumer_id and self.walmart_private_key)


API_CONFIG = ApiConfig()
