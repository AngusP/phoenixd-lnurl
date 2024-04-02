import pytest

from .phoenixd_client import (
    CreateInvoiceResponse,
    PhoenixdMockClient,
)
from .settings import PhoenixdLNURLSettings


@pytest.mark.asyncio
async def test_mock_client_createinvoice():
    settings = PhoenixdLNURLSettings(_env_file="test.env")
    client = PhoenixdMockClient(phoenixd_url=settings.phoenixd_url.get_secret_value())
    inv = await client.createinvoice(
        amount_sat=1337,
        description="demo",
        external_id="test_inv",
    )
    assert (
        CreateInvoiceResponse(
            amountSat=1337,
            paymentHash=(
                "30cf1dfc68ab7c5cd1c79c060d26d001e361e42b19f8cc109178d49833259e92"
            ),
            serialized=(
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
        )
        == inv
    )
