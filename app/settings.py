from pydantic import (
    BaseSettings,
    Field,
    HttpUrl,
    SecretStr,
)
from yarl import URL

MAX_CORN = 21_000_000 * 100_000_000


class PhoenixdLNURLSettings(BaseSettings):
    username: str = Field(regex=r"^[a-z0-9-_\.]+$")
    lnurl_hostname: str
    phoenixd_url: SecretStr

    min_sats_receivable: int = Field(default=1, ge=1)
    max_sats_receivable: int = Field(default=MAX_CORN, ge=1)
    user_profile_image_url: HttpUrl | None = None
    user_nostr_address: str | None = None
    log_level: str = "INFO"

    # Enable development/debug features. Unsafe on prod.
    debug: bool = False
    # Set in test environments. Unsafe on prod.
    is_test: bool = False

    def base_url(self) -> URL:
        # TODO support `http` for `.onion` only (per LNURL spec)
        return URL(f"https://{self.lnurl_hostname}")

    def lnurl_address(self) -> str:
        return f"{self.username}@{self.lnurl_hostname}"

    def is_long_username(self) -> bool:
        return len(self.username) > 10

    class Config:
        env_file = "phoenixd-lnurl.env"
        env_file_encoding = "utf-8"
