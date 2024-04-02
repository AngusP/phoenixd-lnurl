import json

from fastapi.testclient import TestClient
from lnurl import (
    LnurlPayActionResponse,
    LnurlPayResponse,
)

from .main import app_factory

app = app_factory()
test_client = TestClient(app)


def test_read_main():
    response = test_client.get("/")
    assert response.status_code == 400
    assert response.json() == {"status": "ERROR", "reason": "HTTPException "}


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
        "nostr:npub10pensatlcfwktnvjjw2dtem38n6rvw8g6fv73h84cuacxn4c28eqyfn34f"
        in response.text
    )


def test_lnurl_pay_request_lud06_happy():
    response = test_client.get("/lnurlp/satoshi")
    assert LnurlPayResponse.parse_obj(response.json()) == LnurlPayResponse.parse_obj(
        dict(
            callback="https://127.0.0.1/lnurlp/satoshi/callback",
            minSendable=1000,
            maxSendable=500_000,
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
            "RequestValidationError 1 validation error for Request\n"
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
            minSendable=1000,
            maxSendable=500_000,
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
            "RequestValidationError 1 validation error for Request\n"
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
            params=[("amount", 1337 * 1000)],
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
            "RequestValidationError 1 validation error for Request\n"
            "query -> amount\n"
            "  ensure this value is greater than 0 "
            "(type=value_error.number.not_gt; limit_value=0)"
        ),
    }
    assert response.status_code == 400
