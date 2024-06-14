import hashlib
import json

import lnurl
import qrcode.image.svg
from pydantic import (
    BaseSettings,
    Field,
    HttpUrl,
    SecretStr,
)
from qrcode.main import QRCode
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

    # TODO use @computed_field when upgrading to Pydantic 2.x
    # https://docs.pydantic.dev/2.6/api/fields/#pydantic.fields.computed_field
    # So we can also use @functools.cached_property

    def base_url(self) -> URL:
        # TODO support `http` for `.onion` only (per LNURL spec)
        return URL(f"https://{self.lnurl_hostname}")

    def is_long_username(self) -> bool:
        return len(self.username) > 10

    def lnurl_address(self) -> str:
        return f"{self.username}@{self.lnurl_hostname}"

    def lnurl_address_encoded(self) -> lnurl.Lnurl:
        return lnurl.encode(str(self.base_url() / "lnurlp" / self.username))

    def lnurl_qr(self) -> str:
        lnurl_qr = QRCode(
            # NOTE mypy unhappy with passing this class but seems correct
            image_factory=qrcode.image.svg.SvgPathFillImage,  # type: ignore
            box_size=15,
        )
        lnurl_qr.add_data(self.lnurl_address_encoded())
        lnurl_qr.make(fit=True)
        return lnurl_qr.make_image().to_string(encoding="unicode")

    def metadata_for_payrequest(self) -> str:
        return json.dumps(
            [
                ["text/plain", f"Zap {self.username} some sats"],
                ["text/identifier", self.lnurl_address()],
                # ["image/jpeg;base64", "TODO optional"],
            ]
        )

    def metadata_hash(self) -> str:
        return hashlib.sha256(
            self.metadata_for_payrequest().encode("UTF-8")
        ).hexdigest()

    class Config:
        env_file = "phoenixd-lnurl.env"
        env_file_encoding = "utf-8"
