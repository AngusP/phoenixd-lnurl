import json
from hashlib import sha256
from typing import (
    Literal,
    Union,
)

from lnurl.models import LnurlResponseModel
from lnurl.types import (
    ClearnetUrl,
    DebugUrl,
    LnurlPayMetadata,
    MilliSatoshi,
    OnionUrl,
)
from loguru import logger
from pydantic import (
    BaseModel,
    Field,
    validator,
)

# NOTE no type hints available for secp256k1
from secp256k1 import (  # type: ignore
    PrivateKey,
    PublicKey,
)

from .phoenixd_client import IncomingPaymentResponse


class LnurlPayNostrResponse(LnurlResponseModel):
    tag: Literal["payRequest"] = "payRequest"
    callback: Union[ClearnetUrl, OnionUrl, DebugUrl]
    min_sendable: MilliSatoshi = Field(..., alias="minSendable")
    max_sendable: MilliSatoshi = Field(..., alias="maxSendable")
    metadata: LnurlPayMetadata

    comment_allowed: int | None = Field(None, alias="commentAllowed", ge=1)
    allows_nostr: bool | None = Field(None, alias="allowsNostr")
    nostr_pubkey: str | None = Field(None, alias="nostrPubkey")

    @validator("max_sendable")
    def max_less_than_min(cls, value, values, **kwargs):  # noqa
        if "min_sendable" in values and value < values["min_sendable"]:
            raise ValueError("`max_sendable` cannot be less than `min_sendable`.")
        return value

    @validator("nostr_pubkey")
    def check_pubkey(cls, value, values, **kwargs):  # noqa
        if value and value.startswith("n"):
            raise ValueError("nostrPubkey must be hex encoded")
        bytes.fromhex(value)
        return value


class PhoenixdWebsocketNotification(BaseModel):
    hook_type: Literal["payment_received"] = Field(alias="type")
    amount_sat: int = Field(alias="amountSat")
    payment_hash: str = Field(alias="paymentHash")
    external_id: str | None = Field(None, alias="externalId")


class NostrNIP5Response(BaseModel):
    names: dict[str, str]
    relays: dict[str, list[str]]


def get_event_id_NIP1(
    *,
    pubkey: str,
    created_at: int,
    kind: int,
    tags: list[list[str]],
    content: str,
) -> str:
    nip1_format = [
        0,
        pubkey.lower(),
        created_at,
        kind,
        tags,
        content,
    ]
    serialized = json.dumps(
        nip1_format,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256(serialized.encode("UTF-8")).hexdigest()


class NostrZapRequest(BaseModel):
    kind: Literal[9734] = 9734
    nostr_id: str = Field(alias="id")
    sig: str
    pubkey: str
    created_at: int
    tags: list[list[str]]
    content: str

    def _request_amount_msat(self) -> int | None:
        for tag_key, *tag_values in self.tags:
            if tag_key != "amount":
                continue
            if len(tag_values) != 1:
                continue
            return int(tag_values[0])
        return None

    def request_recipient_nostr_key(self) -> str | None:
        p_tag = None
        for tag_key, *tag_values in self.tags:
            if tag_key != "p":
                continue
            if len(tag_values) != 1:
                continue
            if p_tag is not None:
                raise ValueError("Multiple `p` tags in event")
            p_tag = str(tag_values[0])
        return p_tag

    def zapped_event(self) -> str | None:
        e_tag = None
        for tag_key, *tag_values in self.tags:
            if tag_key != "e":
                continue
            if len(tag_values) != 1:
                continue
            if e_tag is not None:
                raise ValueError("Multiple `e` tags in event")
            e_tag = str(tag_values[0])
        return e_tag

    def receipt_relays(self) -> list[str]:
        relays = []
        for tag_key, *tag_values in self.tags:
            if tag_key != "relays":
                continue
            relays = [str(v) for v in tag_values]
        return relays

    def is_valid(
        self,
        amount_msat: int,
        expected_nostr_pubkey: str | None,
    ) -> bool:
        self.verify_signature()
        if nostr_amount := self._request_amount_msat():
            if nostr_amount != amount_msat:
                raise ValueError("Amount does not match")
        if self.request_recipient_nostr_key() != expected_nostr_pubkey:
            raise ValueError("Recipient pubkey doesn't match expected value")
        if self.zapped_event() is None:
            raise ValueError("No 'e' tag in Zap Request")
        # TODO validate tags per https://github.com/nostr-protocol/nips/blob/master/57.md#appendix-d-lnurl-server-zap-request-validation
        return True

    def verify_signature(self) -> bool:
        event_id = get_event_id_NIP1(
            pubkey=self.pubkey.lower(),
            created_at=self.created_at,
            kind=self.kind,
            tags=self.tags,
            content=self.content,
        )
        if event_id != self.nostr_id:
            raise ValueError(
                f"Computed event ID did not match event's given ID ({event_id} != {self.nostr_id})"
            )
        # prefix with `02`` for Schnorr (BIP340)
        public_key = PublicKey(pubkey=bytes.fromhex("02" + self.pubkey), raw=True)
        if not public_key.schnorr_verify(
            msg=bytes.fromhex(event_id),
            schnorr_sig=bytes.fromhex(self.sig),
            bip340tag=None,
            raw=True,
        ):
            raise ValueError("Invalid signature on event")
        return True

    def invoice_description(self) -> str:
        # Per NIP-57, invoices for Zaps should set the invoice's
        # description to the provided zap request note
        return self.json(
            by_alias=True,
            exclude_unset=False,
            # Args to json.dumps:
            ensure_ascii=False,
            separators=(",", ":"),
        )


class NostrZapReceipt(BaseModel):
    kind: Literal[9735] = 9735
    nostr_id: str = Field(alias="id")
    sig: str
    pubkey: str
    created_at: int
    tags: list[list[str]]
    content: str = Field("", max_length=0)

    @classmethod
    def from_zap_request(
        cls,
        *,
        zap_request: NostrZapRequest,
        paid_invoice: IncomingPaymentResponse,
        nostr_pubkey: str,
        nostr_private_key: PrivateKey,
    ) -> "NostrZapReceipt":
        description_tag = zap_request.invoice_description()
        if (
            sha256(description_tag.encode("UTF-8")).hexdigest()
            != sha256((paid_invoice.description or "").encode("UTF-8")).hexdigest()
        ):
            logger.warning("Invoice and Zap Request don't match")
        if (recipient_nostr_key := zap_request.request_recipient_nostr_key()) is None:
            raise ValueError("Couldn't parse recipient Nostr key out of Zap Request")
        if (zapped_event := zap_request.zapped_event()) is None:
            raise ValueError("Can't find the event ID for this Zap Request")
        tags: list[list[str]] = [
            # MUST include the p tag (zap recipient)
            ["p", recipient_nostr_key],
            # AND optional e tag from the zap request
            ["e", zapped_event],
            # AND optional P tag from the pubkey of the zap request (zap sender)
            ["P", zap_request.pubkey],
            # MUST have a bolt11 tag containing the description hash bolt11 invoice
            ["bolt11", paid_invoice.invoice],
            # MUST contain a description tag which is the JSON-encoded invoice description
            ["description", description_tag],
            # MAY contain a preimage tag to match against the payment hash of the bolt11 invoice
            ["preimage", paid_invoice.preimage],
        ]
        # The content SHOULD be empty
        content = ""
        # The created_at date SHOULD be set to the invoice paid_at date
        receipt_creation_timestamp = int(paid_invoice.completed_at.timestamp())

        receipt_event_id = get_event_id_NIP1(
            pubkey=nostr_pubkey,
            created_at=receipt_creation_timestamp,
            kind=9735,
            tags=tags,
            content=content,
        )
        sig = nostr_private_key.schnorr_sign(
            msg=bytes.fromhex(receipt_event_id),
            bip340tag=None,
            raw=True,
        )
        return cls(
            id=receipt_event_id,
            sig=sig.hex(),
            pubkey=nostr_pubkey,
            created_at=receipt_creation_timestamp,
            tags=tags,
            content=content,
        )
