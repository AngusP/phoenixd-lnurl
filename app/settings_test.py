from pydantic import SecretStr
from yarl import URL

from .settings import PhoenixdLNURLSettings


def test_testenv_settings_load():
    settings = PhoenixdLNURLSettings(_env_file="test.env")
    assert settings.is_test is True
    assert settings.debug is True
    assert settings.username == "satoshi"
    assert settings.lnurl_hostname == "127.0.0.1"
    assert settings.phoenixd_url == SecretStr("http://satoshi:hunter2@127.0.0.1:9740")
    assert (
        settings.user_nostr_address
        == "npub10pensatlcfwktnvjjw2dtem38n6rvw8g6fv73h84cuacxn4c28eqyfn34f"
    )
    assert settings.user_profile_image_url == "https://bitcoin.org/satoshi.png"
    assert settings.log_level == "DEBUG"
    assert settings.min_sats_receivable == 1000
    assert settings.max_sats_receivable == 500_000


def test_default_settings_load():
    settings = PhoenixdLNURLSettings(_env_file="phoenixd-lnurl.env.example")
    # NOTE this is not set in the .env but overridden by environment variable:
    assert settings.is_test is True
    assert settings.debug is False
    assert settings.username == "satoshi"
    assert settings.lnurl_hostname == "example.com"
    assert settings.phoenixd_url == SecretStr("http://_:hunter2@127.0.0.1:9740")
    assert settings.user_nostr_address is None
    assert settings.user_profile_image_url is None
    assert settings.log_level == "INFO"
    assert settings.min_sats_receivable == 1
    assert settings.max_sats_receivable == 2.1e15


def test_testenv_settings_derived_properties():
    settings = PhoenixdLNURLSettings(_env_file="test.env")
    assert settings.base_url() == URL("https://127.0.0.1")
    assert settings.lnurl_address() == "satoshi@127.0.0.1"
    assert (
        settings.lnurl_address_encoded()
        == "LNURL1DP68GURN8GHJ7VFJXUHRQT3S9CCJ7MRWW4EXCUP0WDSHGMMNDP5S4SDZXR"
    )
    assert settings.lnurl_qr()[:20] == '<svg width="61.5mm" '
    assert (
        settings.metadata_for_payrequest()
        == '[["text/plain", "Zap satoshi some sats"], ["text/identifier", "satoshi@127.0.0.1"]]'
    )
    assert (
        settings.metadata_hash()
        == "297f16bedbf6942cdc656e19feb46a577a43a87e1f858fd8511ac7144b84f0de"
    )

    assert settings.is_long_username() is False

    settings.username = "marttimalmi"
    assert settings.is_long_username() is True
