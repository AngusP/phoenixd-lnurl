import json

from fastapi.testclient import TestClient
from lnurl import (
    LnurlPayActionResponse,
    LnurlPayResponse,
)

from .main import app_factory
from .models import (
    NostrNIP5Response,
    NostrZapReceipt,
    NostrZapRequest,
)

app = app_factory()
test_client = TestClient(app)


def test_read_main():
    response = test_client.get("/")
    assert response.status_code == 404
    assert response.json() == {"status": "ERROR", "reason": "Error"}


def test_lnurl_get_lud01():
    response = test_client.get("/lnurl")
    assert response.status_code == 200
    assert response.text.startswith("<!DOCTYPE html>")
    # Some basic checks to ensure config from `test.env` made it through:
    assert 'href="lnurlp:satoshi@127.0.0.1"' in response.text
    assert (
        'href="lightning:LNURL1DP68GURN8GHJ7VFJXUHRQT3S9CCJ7MRWW4EXCUP0WDSHGMMNDP5S4SDZXR"'
        in response.text
    )
    assert (
        "nostr:npub1az6txrn8e84tcuvsrpp4u4awgh7samp0dtdy9zcy690xw9ycsm8suq2sze"
        in response.text
    )


def test_nostr_NIP5():
    response = test_client.get("/.well-known/nostr.json")
    assert NostrNIP5Response.parse_obj(response.json()) == NostrNIP5Response.parse_obj(
        dict(
            names=dict(
                satoshi="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf"
            ),
            relays={
                "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf": [
                    "wss://nostr.bitcoin.org",
                ]
            },
        )
    )
    assert response.status_code == 200


def test_lnurl_pay_request_lud06_happy():
    response = test_client.get("/lnurlp/satoshi")
    assert LnurlPayResponse.parse_obj(response.json()) == LnurlPayResponse.parse_obj(
        dict(
            callback="https://127.0.0.1/lnurlp/satoshi/callback",
            # NOTE these are millisat values
            minSendable=1_000_000,
            maxSendable=500_000_000,
            metadata=json.dumps(
                [
                    ["text/plain", "Zap satoshi some sats"],
                    ["text/identifier", "satoshi@127.0.0.1"],
                ]
            ),
        )
    )
    assert response.status_code == 200


def test_lnurl_pay_request_lud06_unknown_user():
    response = test_client.get("/lnurlp/notsatoshi")
    assert response.json() == {
        "status": "ERROR",
        "reason": "Unknown user",
    }
    assert response.status_code == 404


def test_lnurl_pay_request_lud06_bad_user():
    response = test_client.get("/lnurlp/BOBBYTABLES")
    # NOTE this error message is less verbose when `DEBUG=False`
    assert response.json() == {
        "status": "ERROR",
        "reason": (
            "1 validation error for Request\n"
            "path -> username\n"
            '  string does not match regex "^[a-z0-9-_\\.]+$" '
            "(type=value_error.str.regex; pattern=^[a-z0-9-_\\.]+$)"
        ),
    }
    assert response.status_code == 400


def test_lnurl_pay_request_lud16_happy():
    response = test_client.get("/.well-known/lnurlp/satoshi")
    assert LnurlPayResponse.parse_obj(response.json()) == LnurlPayResponse.parse_obj(
        dict(
            callback="https://127.0.0.1/lnurlp/satoshi/callback",
            # NOTE these are millisat values
            minSendable=1_000_000,
            maxSendable=500_000_000,
            metadata=json.dumps(
                [
                    ["text/plain", "Zap satoshi some sats"],
                    ["text/identifier", "satoshi@127.0.0.1"],
                ]
            ),
        )
    )
    assert response.status_code == 200


def test_lnurl_pay_request_lud16_unknown_user():
    response = test_client.get("/.well-known/lnurlp/notsatoshi")
    assert response.json() == {
        "status": "ERROR",
        "reason": "Unknown user",
    }
    assert response.status_code == 404


def test_lnurl_pay_request_lud16_bad_user():
    response = test_client.get("/.well-known/lnurlp/BOBBYTABLES")
    # NOTE this error message is less verbose when `DEBUG=False`
    assert response.json() == {
        "status": "ERROR",
        "reason": (
            "1 validation error for Request\n"
            "path -> username\n"
            '  string does not match regex "^[a-z0-9-_\\.]+$" '
            "(type=value_error.str.regex; pattern=^[a-z0-9-_\\.]+$)"
        ),
    }
    assert response.status_code == 400


def test_lnurl_pay_request_callback_lud06_happy():
    # NOTE we need to use a test client context to ensure lifespan
    # startup/teardown code is run, otherwise `app.state...` may not exist
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback",
            # NOTE the amount here is millisatoshis
            params=[
                ("amount", 1337 * 1000),
                ("comment", "Onwards! 🫡"),
            ],
        )
    assert LnurlPayActionResponse.parse_obj(
        response.json()
    ) == LnurlPayActionResponse.parse_obj(
        dict(
            pr=(
                "lntb1u1pnquurmpp5xr83mlrg4d79e5w8nsrq6fksq83kreptr8uvcyy3"
                "0r2fsve9n6fqcqpjsp5ut3l5lvwpwyjcqf508nzdtze65zl2yycm45uee"
                "elktu3phzv2fsq9q7sqqqqqqqqqqqqqqqqqqqsqqqqqysgqdrytddjyar"
                "90p69ctmsd3skjm3z9s395ctsypekzar0wd5xjgja93djyar90p69ctmf"
                "v3jkuarfve5k2u3z9s38xct5daeks6fzt4wsmqz9grzjqwfn3p9278ttz"
                "zpe0e00uhyxhned3j5d9acqak5emwfpflp8z2cnflcdkeu6euv7gsqqqq"
                "lgqqqqqeqqjqvyrulmkm8x58s9vahdm3z7jlj00pgl04xhfd0gjlm0e5e"
                "z7llfg49ra6pl96808deh95ysvmxajhfse4033k2deh58mrgdjj8kz8s6"
                "gpd82r8j"
            ),
            routes=[],
            success_action={
                "tag": "message",
                "message": "Thanks for zapping satoshi",
            },
        )
    )
    assert response.status_code == 200


def test_lnurl_pay_request_callback_lud06_unknown_user():
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/notsatoshi/callback",
            params=[("amount", 1337000)],
        )
    assert response.json() == {
        "status": "ERROR",
        "reason": "Unknown user",
    }
    assert response.status_code == 404


def test_lnurl_pay_request_callback_lud06_amount_too_low():
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback",
            # 1000 mSat == 1 sat
            params=[("amount", 1000)],
        )
    assert response.json() == {
        "status": "ERROR",
        "reason": "Amount is too low, minimum is 1000 sats",
    }
    assert response.status_code == 400


def test_lnurl_pay_request_callback_lud06_amount_too_high():
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback", params=[("amount", 500_001_000)]
        )
    assert response.json() == {
        "status": "ERROR",
        "reason": "Amount is too high, maximum is 500000 sats",
    }
    assert response.status_code == 400


def test_lnurl_pay_request_callback_lud06_bad_amount():
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback", params=[("amount", -100_000)]
        )
    assert response.json() == {
        "status": "ERROR",
        "reason": (
            "1 validation error for Request\n"
            "query -> amount\n"
            "  ensure this value is greater than 0 "
            "(type=value_error.number.not_gt; limit_value=0)"
        ),
    }
    assert response.status_code == 400


def test_lnurl_pay_request_callback_lud06_nostr_happy():
    # NOTE the amount here is millisatoshis
    amount = 1337 * 1000
    zap_request = NostrZapRequest(
        kind=9734,
        id="c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
        sig="6e620802ec934fdc7580df54a852161e9732414d0963c10de9f42b831065cf139b8e9f8aa333b4281376d4c42b281d48e5ece4643f8a42091a4788da3a1fe116",
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
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback",
            params=[
                ("amount", amount),
                ("nostr", zap_request.json(by_alias=True, exclude_unset=False)),
            ],
        )
    assert LnurlPayActionResponse.parse_obj(
        response.json()
    ) == LnurlPayActionResponse.parse_obj(
        dict(
            pr=(
                "lntb1u1pnquurmpp5xr83mlrg4d79e5w8nsrq6fksq83kreptr8uvcyy3"
                "0r2fsve9n6fqcqpjsp5ut3l5lvwpwyjcqf508nzdtze65zl2yycm45uee"
                "elktu3phzv2fsq9q7sqqqqqqqqqqqqqqqqqqqsqqqqqysgqdrytddjyar"
                "90p69ctmsd3skjm3z9s395ctsypekzar0wd5xjgja93djyar90p69ctmf"
                "v3jkuarfve5k2u3z9s38xct5daeks6fzt4wsmqz9grzjqwfn3p9278ttz"
                "zpe0e00uhyxhned3j5d9acqak5emwfpflp8z2cnflcdkeu6euv7gsqqqq"
                "lgqqqqqeqqjqvyrulmkm8x58s9vahdm3z7jlj00pgl04xhfd0gjlm0e5e"
                "z7llfg49ra6pl96808deh95ysvmxajhfse4033k2deh58mrgdjj8kz8s6"
                "gpd82r8j"
            ),
            routes=[],
            success_action={
                "tag": "message",
                "message": "Thanks for zapping satoshi",
            },
        )
    )
    assert response.status_code == 200


def test_lnurl_pay_request_callback_lud06_nostr_unparsable_zap_request():
    # NOTE the amount here is millisatoshis
    amount = 1337 * 1000
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback",
            params=[
                ("amount", amount),
                # Un-parsable zap_request should be ignored
                ("nostr", {"kind": 9734, "id": "None"}),
            ],
        )
    assert LnurlPayActionResponse.parse_obj(
        response.json()
    ) == LnurlPayActionResponse.parse_obj(
        dict(
            pr=(
                "lntb1u1pnquurmpp5xr83mlrg4d79e5w8nsrq6fksq83kreptr8uvcyy3"
                "0r2fsve9n6fqcqpjsp5ut3l5lvwpwyjcqf508nzdtze65zl2yycm45uee"
                "elktu3phzv2fsq9q7sqqqqqqqqqqqqqqqqqqqsqqqqqysgqdrytddjyar"
                "90p69ctmsd3skjm3z9s395ctsypekzar0wd5xjgja93djyar90p69ctmf"
                "v3jkuarfve5k2u3z9s38xct5daeks6fzt4wsmqz9grzjqwfn3p9278ttz"
                "zpe0e00uhyxhned3j5d9acqak5emwfpflp8z2cnflcdkeu6euv7gsqqqq"
                "lgqqqqqeqqjqvyrulmkm8x58s9vahdm3z7jlj00pgl04xhfd0gjlm0e5e"
                "z7llfg49ra6pl96808deh95ysvmxajhfse4033k2deh58mrgdjj8kz8s6"
                "gpd82r8j"
            ),
            routes=[],
            success_action={
                "tag": "message",
                "message": "Thanks for zapping satoshi",
            },
        )
    )
    assert response.status_code == 200


def test_lnurl_pay_request_callback_lud06_nostr_invalid_zap_request():
    # NOTE the amount here is millisatoshis
    amount = 1337 * 1000
    zap_request = NostrZapRequest(
        kind=9734,
        id="c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
        # Signature is missing so request will obviously fail Nostr validation
        sig="",
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
    with TestClient(app) as local_client:
        response = local_client.get(
            "/lnurlp/satoshi/callback",
            params=[
                ("amount", amount),
                ("nostr", zap_request.json(by_alias=True, exclude_unset=False)),
            ],
        )
    # If we got something that looked like a Zap Request but couldn't handle it
    # we return an error rather than continue with plain LNURL
    assert response.json() == {
        "status": "ERROR",
        "reason": "Invalid NIP-57 Zap Request event: Invalid signature on event",
    }
    assert response.status_code == 400


def test_phoenixd_webhook_happy():
    zap_request = NostrZapRequest(
        kind=9734,
        id="c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
        sig="6e620802ec934fdc7580df54a852161e9732414d0963c10de9f42b831065cf139b8e9f8aa333b4281376d4c42b281d48e5ece4643f8a42091a4788da3a1fe116",
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
    with TestClient(app) as local_client:
        response = local_client.post(
            "/phoenixd-webhook",
            json=dict(
                type="payment_received",
                amountSat=10,
                paymentHash="30cf1dfc68ab7c5cd1c79c060d26d001e361e42b19f8cc109178d49833259e92",
                externalId="zap-c66329d84a2acf1c11296b3efc42931dd00d76b8bfb8e5b37d43bff8fa921914",
            ),
        )
    assert response.json() == {
        "status": "ok",
        "receipt": NostrZapReceipt(
            kind=9735,
            id="d0c7e1dc8712c662c76dac9016bcf452cb31bd46c81fdc7feedebef5f760578d",
            sig="6f4450f447de758fbdb95a81acbc194c5be90888ba1dd68f0fcea75656f8de887f63b46aca5f3a6be8a17411e4a6b163718de59fe56cf29fcf706a754bf9c110",
            pubkey="e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
            created_at=1713300291,
            tags=[
                [
                    "p",
                    "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
                ],
                [
                    "e",
                    "4af818a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc57322",
                ],
                [
                    "P",
                    "e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886cf",
                ],
                [
                    "bolt11",
                    "lntb1u1pnquurmpp5xr83mlrg4d79e5w8nsrq6fksq83kreptr8uvcyy3"
                    "0r2fsve9n6fqcqpjsp5ut3l5lvwpwyjcqf508nzdtze65zl2yycm45uee"
                    "elktu3phzv2fsq9q7sqqqqqqqqqqqqqqqqqqqsqqqqqysgqdrytddjyar"
                    "90p69ctmsd3skjm3z9s395ctsypekzar0wd5xjgja93djyar90p69ctmf"
                    "v3jkuarfve5k2u3z9s38xct5daeks6fzt4wsmqz9grzjqwfn3p9278ttz"
                    "zpe0e00uhyxhned3j5d9acqak5emwfpflp8z2cnflcdkeu6euv7gsqqqq"
                    "lgqqqqqeqqjqvyrulmkm8x58s9vahdm3z7jlj00pgl04xhfd0gjlm0e5e"
                    "z7llfg49ra6pl96808deh95ysvmxajhfse4033k2deh58mrgdjj8kz8s6"
                    "gpd82r8j",
                ],
                ["description", zap_request.invoice_description()],
                [
                    "preimage",
                    "ee42430339e9d9c88b8b25f6d82eced562af242f0c24cbd728582992b804d168",
                ],
            ],
            content="",
        ).dict(
            by_alias=True,
            exclude_unset=False,
        ),
    }
    assert response.status_code == 200


def test_phoenixd_webhook_happy_not_a_zap():
    with TestClient(app) as local_client:
        response = local_client.post(
            "/phoenixd-webhook",
            json=dict(
                type="payment_received",
                amountSat=10,
                paymentHash="30cf1dfc68ab7c5cd1c79c060d26d001e361e42b19f8cc109178d49833259e92",
                externalId="lnurl-297f16bedbf6942cdc656e19feb46a577a43a87e1f858fd8511ac7144b84f0de",
            ),
        )
    assert response.json() == {"status": "ok"}
    assert response.status_code == 200
