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
    assert settings.lnurl_hostname == "bitcoincore.org"
    assert settings.phoenixd_url == SecretStr("http://satoshi:hunter2@127.0.0.1:9740")
    assert settings.user_nostr_address is None
    assert settings.user_profile_image_url is None
    assert settings.log_level == "INFO"
    assert settings.min_sats_receivable == 1
    assert settings.max_sats_receivable == 2.1e15


def test_testenv_settings_derived_properties():
    settings = PhoenixdLNURLSettings(_env_file="test.env")
    assert settings.base_url() == URL("https://127.0.0.1")
    assert settings.lnurl_address() == "satoshi@127.0.0.1"
    assert settings.is_long_username() is False

    settings.username = "marttimalmi"
    assert settings.is_long_username() is True
