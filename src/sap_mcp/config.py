from __future__ import annotations

from pydantic_settings import BaseSettings


class SAPSettings(BaseSettings):
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


settings = SAPSettings()
