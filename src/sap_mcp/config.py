from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_settings import BaseSettings


class SAPSettings(BaseSettings):
    """Single-system settings from SAP_ env vars (stdio mode / test fallback)."""

    model_config = {"env_prefix": "SAP_"}

    ashost: str = "localhost"
    sysnr: str = "00"
    client: str = "100"
    user: str = "RFC_USER"
    passwd: str = ""
    lang: str = "EN"
    mock_mode: bool = True
    connection_pool_size: int = 5

    def connection_params(self) -> dict[str, str]:
        return {
            "ashost": self.ashost,
            "sysnr": self.sysnr,
            "client": self.client,
            "user": self.user,
            "passwd": self.passwd,
            "lang": self.lang,
        }


# Backward-compatible env-based singleton (used by the default pool and stdio mode).
settings = SAPSettings()


@dataclass
class SAPConfig:
    """Connection config for one country/SAP system.

    Shares the interface used by ConnectionManager (`connection_params()`,
    `mock_mode`, `connection_pool_size`) so it is interchangeable with SAPSettings.
    """

    ashost: str = "localhost"
    sysnr: str = "00"
    client: str = "100"
    user: str = "RFC_USER"
    passwd: str = ""
    lang: str = "EN"
    mock_mode: bool = True
    connection_pool_size: int = 5

    def connection_params(self) -> dict[str, str]:
        return {
            "ashost": self.ashost,
            "sysnr": self.sysnr,
            "client": self.client,
            "user": self.user,
            "passwd": self.passwd,
            "lang": self.lang,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SAPConfig":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


# Path to the per-country JSON config (mounted as a volume in Docker).
COUNTRIES_FILE = os.getenv("SAP_COUNTRIES_FILE", "/app/countries.json")


def load_countries() -> dict[str, SAPConfig]:
    """Load {country_code: SAPConfig} from the JSON config file.

    The file maps lowercase country codes to objects of SAP connection fields.
    Missing fields fall back to SAPConfig defaults. If the file is absent, a
    single "default" country is synthesised from the SAP_ env vars so the server
    still boots (mock mode by default).
    """
    path = Path(COUNTRIES_FILE)
    if not path.is_file():
        return {"default": SAPConfig(**settings.model_dump())}

    raw = json.loads(path.read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            f"{COUNTRIES_FILE} must be a non-empty JSON object "
            '{"<code>": {ashost, client, user, ...}}'
        )

    countries: dict[str, SAPConfig] = {}
    for code, cfg in raw.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"Country '{code}' must map to an object of SAP fields")
        countries[code.lower()] = SAPConfig.from_dict(cfg)
    return countries
