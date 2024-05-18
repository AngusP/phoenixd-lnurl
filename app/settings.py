import hashlib
import json

import bech32
import lnurl
import qrcode.image.svg
from pydantic import (
    BaseSettings,
    Field,
    HttpUrl,
    SecretStr,
    validator,
)
from qrcode.main import QRCode

# NOTE no type hints available for secp256k1
from secp256k1 import (  # type: ignore
    PrivateKey,
    PublicKey,
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
    user_nostr_address: str | None = None  # npub
    user_nostr_private_key: SecretStr | None = None  # nsec
    nostr_relays: list[str] | None = None
    log_level: str = "INFO"

    # Enable development/debug features. Unsafe on prod.
    debug: bool = False
    # Set in test environments. Unsafe on prod.
    is_test: bool = False

    # TODO use @computed_field when upgrading to Pydantic 2.x
    # https://docs.pydantic.dev/2.6/api/fields/#pydantic.fields.computed_field
    # So we can also use @functools.cached_property

    @validator("user_nostr_private_key", always=True)
    def check_nsec_matches_npub(cls, value, values):
        if value is None:
            return None
        if (npub := values.get("user_nostr_address")) is None:
            raise ValueError(
                "Must have USER_NOSTR_ADDRESS if providing USER_NOSTR_PRIVATE_KEY"
            )

        pubkey_hex = (
            PublicKey(pubkey=bytes.fromhex("02" + npub_to_hex(npub)), raw=True)
            .serialize()
            .hex()
        )

        hrp, data = bech32.bech32_decode(value.get_secret_value())
        if hrp != "nsec":
            raise ValueError("USER_NOSTR_PRIVATE_KEY must be an 'nsec'")
        if data is None:
            raise ValueError("Couldn't decode USER_NOSTR_PRIVATE_KEY (expected nsec)")

        maybe_raw_private_key = bech32.convertbits(data, 5, 8)
        del data
        if maybe_raw_private_key is None:
            raise ValueError("Couldn't decode USER_NOSTR_PRIVATE_KEY (expected nsec)")
        raw_private_key = bytes(maybe_raw_private_key[:-1])
        del maybe_raw_private_key
        privkey = PrivateKey(privkey=raw_private_key, raw=True)
        del raw_private_key
        derived_pubkey_hex = privkey.pubkey.serialize().hex()
        del privkey

        if derived_pubkey_hex != pubkey_hex:
            raise ValueError(
                "Public key for provided USER_NOSTR_PRIVATE_KEY does not match USER_NOSTR_ADDRESS"
            )

        return value

    def nostr_private_key(self) -> PrivateKey:
        if self.user_nostr_private_key is None:
            raise ValueError("USER_NOSTR_PRIVATE_KEY is not set")
        hrp, data = bech32.bech32_decode(self.user_nostr_private_key.get_secret_value())
        if hrp != "nsec":
            raise ValueError("USER_NOSTR_PRIVATE_KEY must be an 'nsec'")
        if data is None:
            raise ValueError("Couldn't decode USER_NOSTR_PRIVATE_KEY (expected nsec)")
        maybe_raw_private_key = bech32.convertbits(data, 5, 8)
        del data
        if maybe_raw_private_key is None:
            raise ValueError("Couldn't decode USER_NOSTR_PRIVATE_KEY (expected nsec)")
        raw_private_key = bytes(maybe_raw_private_key[:-1])
        del maybe_raw_private_key
        privkey = PrivateKey(privkey=raw_private_key, raw=True)
        del raw_private_key
        return privkey

    def supports_nostr_zaps(self) -> bool:
        # Private key (nsec) is required for Zaps so we can create Zap Receipts (NIP-57)
        return (
            self.user_nostr_private_key is not None
            and self.user_nostr_address is not None
        )

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
            ]
        )

    def metadata_hash(self) -> str:
        return hashlib.sha256(
            self.metadata_for_payrequest().encode("UTF-8")
        ).hexdigest()

    def user_nostr_address_hex(self) -> str | None:
        if not self.user_nostr_address:
            return None
        return npub_to_hex(self.user_nostr_address)

    class Config:
        env_file = "phoenixd-lnurl.env"
        env_file_encoding = "utf-8"


def npub_to_hex(npub: str) -> str | None:
    hrp, data = bech32.bech32_decode(npub)
    if hrp != "npub":
        return None
    if data is None:
        return None
    maybe_raw_public_key = bech32.convertbits(data, 5, 8)
    if maybe_raw_public_key is None:
        return None
    raw_public_key = maybe_raw_public_key[:-1]
    return bytes(raw_public_key).hex()
