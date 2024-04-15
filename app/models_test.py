from datetime import datetime

import pytest
from secp256k1 import PrivateKey  # type: ignore

from .models import (
    NostrZapReceipt,
    NostrZapRequest,
)
from .phoenixd_client import IncomingPaymentResponse


def test_nostr_zap_request_happy():
    zap_request = NostrZapRequest(
        kind=9734,
        id="c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
        sig=(
            "6e620802ec934fdc7580df54a852161e9732414d0963c10de9f42b831065cf13"
            "9b8e9f8aa333b4281376d4c42b281d48e5ece4643f8a42091a4788da3a1fe116"
        ),
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722971,
        tags=[
            ["p", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["amount", "1337000"],
            [
                "relays",
                "wss://relay.nostr.band/",
                "wss://nos.lol/",
                "wss://relay.damus.io/",
            ],
            ["e", "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"],
        ],
        content="",
    )
    assert (
        zap_request.is_valid(
            amount_msat=1337000,
            expected_nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        )
        is True
    )
    assert (
        zap_request.request_recipient_nostr_key()
        == "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"
    )
    assert (
        zap_request.zapped_event()
        == "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"
    )
    assert zap_request.receipt_relays() == [
        "wss://relay.nostr.band/",
        "wss://nos.lol/",
        "wss://relay.damus.io/",
    ]
    assert zap_request.invoice_description() == (
        '{"kind":9734,"id":"c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d'
        '43bff8fa921914","sig":"6e620802ec934fdc7580df54a852161e9732414d0963c1'
        "0de9f42b831065cf139b8e9f8aa333b4281376d4c42b281d48e5ece4643f8a42091a4"
        '788da3a1fe116","pubkey":"e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada'
        '428b04d15e67149886cf","created_at":1713722971,"tags":[["p","e8b4b30e6'
        '7c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],["amount","'
        '1337000"],["relays","wss://relay.nostr.band/","wss://nos.lol/","wss:/'
        '/relay.damus.io/"],["e","4af818a397daa226a85e8012197bee9ac4fd9cce85b4'
        '949334481d0c5bc57322"]],"content":""}'
    )


def test_nostr_zap_receipt_happy():
    zap_request = NostrZapRequest(
        kind=9734,
        id="c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
        sig=(
            "6e620802ec934fdc7580df54a852161e9732414d0963c10de9f42b831065cf13"
            "9b8e9f8aa333b4281376d4c42b281d48e5ece4643f8a42091a4788da3a1fe116"
        ),
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722971,
        tags=[
            ["p", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["amount", "1337000"],
            [
                "relays",
                "wss://relay.nostr.band/",
                "wss://nos.lol/",
                "wss://relay.damus.io/",
            ],
            ["e", "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"],
        ],
        content="",
    )
    assert zap_request.is_valid(
        amount_msat=1337000,
        expected_nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
    )
    nostr_private_key = PrivateKey(
        privkey=bytes.fromhex(
            "661a629b00517e6c55f75eeead359510abe1f2c04e06531abafb3e666fcaafaf"
        ),
        raw=True,
    )
    paid_invoice = IncomingPaymentResponse(
        paymentHash="paymentHash",
        preimage="preimage",
        invoice="lntb....",
        isPaid=True,
        receivedSat=1337,
        fees=1,
        completedAt=datetime.fromtimestamp(1713722981),
        createdAt=datetime.fromtimestamp(1713722971),
        description=zap_request.invoice_description(),
        externalId="zap-2612f615-226d-48f2-a4d1-6b89f6747914",
    )
    zap_receipt = NostrZapReceipt.from_zap_request(
        zap_request=zap_request,
        paid_invoice=paid_invoice,
        nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        nostr_private_key=nostr_private_key,
    )
    assert zap_receipt == NostrZapReceipt(
        kind=9735,
        id="6d3892986f47970746d89455086dec66f06eed32dcea211c4c2cefd7f2e75e10",
        sig="998d68f150418fc4e55d670d3217c78d862dafc56e5551f6ee49c2b7899825e9c3f3cf93e2b3024013f4a1798bc868cb8a4edb07fbf2e48734f78a728bed9049",
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722981,
        tags=[
            ["p", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["e", "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"],
            ["P", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["bolt11", "lntb...."],
            ["description", zap_request.invoice_description()],
            ["preimage", "preimage"],
        ],
        content="",
    )


def test_nostr_zap_request_invalid_id():
    zap_request = NostrZapRequest(
        kind=9734,
        # Incorrect ID for the event
        id="missing",
        sig=(
            "6e620802ec934fdc7580df54a852161e9732414d0963c10de9f42b831065cf13"
            "9b8e9f8aa333b4281376d4c42b281d48e5ece4643f8a42091a4788da3a1fe116"
        ),
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722971,
        tags=[
            ["p", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["amount", "1337000"],
            [
                "relays",
                "wss://relay.nostr.band/",
                "wss://nos.lol/",
                "wss://relay.damus.io/",
            ],
            ["e", "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"],
        ],
        content="",
    )
    with pytest.raises(ValueError) as exc_info:
        zap_request.is_valid(
            amount_msat=1337000,
            expected_nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        )
    assert exc_info.value.args[0] == (
        "Computed event ID did not match event's given ID "
        "(c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914 != missing)"
    )


def test_nostr_zap_request_invalid_signature():
    zap_request = NostrZapRequest(
        kind=9734,
        id="c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
        # Signature from a different event
        sig="bb31687b6bfa319339008f7fcd862430109b9969771cdff4218828b13cbbf3cc82aa75a593019972d8b3d0f45777809a3fa5e81d7d26567e4db8ca2582038c22",
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722971,
        tags=[
            ["p", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["amount", "1337000"],
            [
                "relays",
                "wss://relay.nostr.band/",
                "wss://nos.lol/",
                "wss://relay.damus.io/",
            ],
            ["e", "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"],
        ],
        content="",
    )
    with pytest.raises(ValueError) as exc_info:
        zap_request.is_valid(
            amount_msat=1337000,
            expected_nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        )
    assert exc_info.value.args[0] == "Invalid signature on event"


def test_nostr_zap_request_invalid_recipient_pubkey():
    zap_request = NostrZapRequest(
        kind=9734,
        id="479f36282977c0d22b80d28b5d42c1c6a978d19b7d440707430e889758849d23",
        sig="bf6c5268a0d56a7c9f563aadc953bef8383574c81e85671bd0f526e0637663335e63f9ac1368543351783e77a4fc4a55c01c9e43d5233facccf1547679fad921",
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722971,
        tags=[
            # Not our pubkey
            ["p", "84dee6e676e5bb67b4ad4e042cf70cbd8681155db535942fcc6a0533858a7240"],
            ["amount", "1337000"],
            [
                "relays",
                "wss://relay.nostr.band/",
                "wss://nos.lol/",
                "wss://relay.damus.io/",
            ],
            ["e", "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322"],
        ],
        content="",
    )
    with pytest.raises(ValueError) as exc_info:
        zap_request.is_valid(
            amount_msat=1337000,
            expected_nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        )
    assert exc_info.value.args[0] == "Recipient pubkey doesn't match expected value"


def test_nostr_zap_request_invalid_missing_e_tag():
    zap_request = NostrZapRequest(
        kind=9734,
        id="082615a1887fdb49528e5ab141629c1b7c392d37ae904ae788bf0fed38cdbdc3",
        sig="64648fea2fc883e042683c1f679fe4cb163bcc5f361179ec9966118345217333ad9e560247f27a7620eb3d9175c1f63999017916d2524e47a9c83b4fa72f29f9",
        pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        created_at=1713722971,
        tags=[
            ["p", "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"],
            ["amount", "1337000"],
            [
                "relays",
                "wss://relay.nostr.band/",
                "wss://nos.lol/",
                "wss://relay.damus.io/",
            ],
        ],
        content="",
    )
    with pytest.raises(ValueError) as exc_info:
        zap_request.is_valid(
            amount_msat=1337000,
            expected_nostr_pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
        )
    assert exc_info.value.args[0] == "No 'e' tag in Zap Request"
