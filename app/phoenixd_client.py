from abc import (
    ABC,
    abstractmethod,
)
from datetime import datetime
from typing import Any

import aiohttp
from loguru import logger
from pydantic import (
    BaseModel,
    Extra,
    Field,
)
from yarl import URL

MAX_DESCRIPTION = 128


class ChannelInfo(BaseModel, extra=Extra.ignore):
    state: str
    channel_id: str = Field(alias="channelId")
    balance_dat: int = Field(alias="balanceSat", ge=0)
    inbound_liquidity_sat: int = Field(alias="inboundLiquiditySat", ge=0)
    capacity_sat: int = Field(alias="capacitySat", ge=0)
    funding_tx_id: str = Field(alias="fundingTxId")


class GetInfoResponse(BaseModel, extra=Extra.ignore):
    node_id: str = Field(alias="nodeId")
    channels: list[ChannelInfo]
    chain: str
    version: str


class GetBalanceResponse(BaseModel, extra=Extra.ignore):
    balance_sat: int = Field(alias="balanceSat", ge=0)
    fee_credit_sat: int = Field(alias="feeCreditSat", ge=0)


class ListChannelsResponse(BaseModel, extra=Extra.ignore):
    channels: list[dict]


class CreateInvoiceResponse(BaseModel, extra=Extra.ignore):
    amount_sat: int = Field(alias="amountSat", ge=0)
    payment_hash: str = Field(alias="paymentHash")
    serialized: str


class IncomingPaymentResponse(BaseModel, extra=Extra.ignore):
    payment_hash: str = Field(alias="paymentHash")
    preimage: str
    invoice: str
    is_paid: bool = Field(alias="isPaid")
    received_sat: int = Field(alias="receivedSat")
    fees: int
    completed_at: datetime = Field(alias="completedAt")
    created_at: datetime = Field(alias="createdAt")
    description: str | None
    external_id: str | None = Field(alias="externalId")


class PhoenixdClientBase(ABC):
    @abstractmethod
    async def getinfo(self) -> GetInfoResponse: ...

    @abstractmethod
    async def getbalance(self) -> GetBalanceResponse: ...

    @abstractmethod
    async def listchannels(self) -> ListChannelsResponse: ...

    @abstractmethod
    async def closechannel(
        self,
        *,
        channel_id: str,
        address: str,
        feerate_sat_vbyte: int,
    ): ...

    @abstractmethod
    async def createinvoice(
        self,
        *,
        amount_sat: int,
        description: str | None,
        description_hash: str | None = None,
        external_id: str | None = None,
    ) -> CreateInvoiceResponse: ...

    @abstractmethod
    async def payinvoice(
        self,
        *,
        invoice: str,
        amount_sat: int | None = None,
    ): ...

    @abstractmethod
    async def sendtoaddress(
        self,
        *,
        address: str,
        amount_sat: int,
        feerate_sat_vbyte: int,
    ): ...

    @abstractmethod
    async def incoming_payments_external_id(
        self, external_id: str
    ) -> list[IncomingPaymentResponse]: ...

    @abstractmethod
    async def incoming_payment_hash(
        self, payment_hash: str
    ) -> IncomingPaymentResponse: ...

    @abstractmethod
    async def outgoing_payment_id(self, payment_id: str): ...

    @abstractmethod
    async def payments_websocket(self): ...


class PhoenixdHttpClient(PhoenixdClientBase):
    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        phoenixd_url: str | URL,
    ):
        self.session = session
        self.baseurl = (
            phoenixd_url if isinstance(phoenixd_url, URL) else URL(phoenixd_url)
        )

    async def getinfo(self) -> GetInfoResponse:
        async with self.session.get(self.baseurl / "getinfo") as response:
            return GetInfoResponse.parse_obj(await response.json())

    async def getbalance(self) -> GetBalanceResponse:
        async with self.session.get(self.baseurl / "getbalance") as response:
            return GetBalanceResponse.parse_obj(await response.json())

    async def listchannels(self) -> ListChannelsResponse:
        async with self.session.get(self.baseurl / "listchannels") as response:
            return ListChannelsResponse.parse_obj(await response.json())

    async def closechannel(
        self,
        *,
        channel_id: str,
        address: str,
        feerate_sat_vbyte: int,
    ):
        raise NotImplementedError()

    async def createinvoice(
        self,
        *,
        amount_sat: int,
        description: str | None,
        description_hash: str | None = None,
        external_id: str | None = None,
    ) -> CreateInvoiceResponse:
        form_data: dict[str, Any] = {
            "amountSat": amount_sat,
        }
        description_for_form(form_data, description, description_hash)

        if external_id is not None:
            form_data["externalId"] = external_id

        async with self.session.post(
            self.baseurl / "createinvoice",
            data=form_data,
        ) as response:
            if response.status != 200:
                raise ValueError(
                    f"Error creating invoice, Phoenixd responded non-200: {await response.text()}"
                )
            invoice = CreateInvoiceResponse.parse_obj(await response.json())
        logger.info(
            "Created invoice {inv_short}... externalId: '{external_id}'",
            inv_short=invoice.serialized[:12],
            external_id=external_id,
        )
        logger.debug("Invoice: {invoice}", invoice=invoice)
        return invoice

    async def payinvoice(
        self,
        *,
        invoice: str,
        amount_sat: int | None = None,
    ):
        raise NotImplementedError()

    async def sendtoaddress(
        self,
        *,
        address: str,
        amount_sat: int,
        feerate_sat_vbyte: int,
    ):
        raise NotImplementedError()

    async def incoming_payments_external_id(
        self, external_id: str
    ) -> list[IncomingPaymentResponse]:
        async with self.session.get(
            self.baseurl / "payments" / "incoming",
            params=[("externalId", external_id)],
        ) as response:
            return [
                IncomingPaymentResponse.parse_obj(payment)
                for payment in await response.json()
            ]

    async def incoming_payment_hash(self, payment_hash: str) -> IncomingPaymentResponse:
        async with self.session.get(
            self.baseurl / "payments" / "incoming" / payment_hash,
        ) as response:
            return IncomingPaymentResponse.parse_obj(await response.json())

    async def outgoing_payment_id(self, payment_id: str):
        raise NotImplementedError()

    async def payments_websocket(self):
        raise NotImplementedError()


class PhoenixdMockClient(PhoenixdClientBase):
    def __init__(
        self,
        *,
        phoenixd_url: str | URL,
    ):
        self.baseurl = (
            phoenixd_url if isinstance(phoenixd_url, URL) else URL(phoenixd_url)
        )

    async def getinfo(self) -> GetInfoResponse:
        raise NotImplementedError()

    async def getbalance(self) -> GetBalanceResponse:
        raise NotImplementedError()

    async def listchannels(self) -> ListChannelsResponse:
        raise NotImplementedError()

    async def closechannel(
        self,
        *,
        channel_id: str,
        address: str,
        feerate_sat_vbyte: int,
    ):
        raise NotImplementedError()

    async def createinvoice(
        self,
        *,
        amount_sat: int,
        description: str | None,
        description_hash: str | None = None,
        external_id: str | None = None,
    ) -> CreateInvoiceResponse:
        form_data: dict[str, str] = dict()
        description_for_form(form_data, description, description_hash)
        invoice = CreateInvoiceResponse.parse_obj(
            {
                "amountSat": amount_sat,
                "paymentHash": (
                    "30cf1dfc68ab7c5cd1c79c060d26d001e361e42b19f8cc109178d4983"
                    "3259e92"
                ),
                "serialized": (
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
            }
        )
        logger.info(
            "Created invoice {inv_short}... externalId: '{external_id}'",
            inv_short=invoice.serialized[:12],
            external_id=external_id,
        )
        logger.debug("Invoice: {invoice}", invoice=invoice)
        return invoice

    async def payinvoice(
        self,
        *,
        invoice: str,
        amount_sat: int | None = None,
    ):
        raise NotImplementedError()

    async def sendtoaddress(
        self,
        *,
        address: str,
        amount_sat: int,
        feerate_sat_vbyte: int,
    ):
        raise NotImplementedError()

    async def incoming_payments_external_id(
        self, external_id: str
    ) -> list[IncomingPaymentResponse]:
        raise NotImplementedError()

    async def incoming_payment_hash(self, payment_hash: str) -> IncomingPaymentResponse:
        return IncomingPaymentResponse.parse_obj(
            {
                "paymentHash": payment_hash,
                "preimage": "ee42430339e9d9c88b8b25f6d82eced562af242f0c24cbd728582992b804d168",
                "externalId": "zap-49c9dccc-12b5-486d-ad00-4bf76eaf8c5f",
                "description": (
                    '{"kind":9734,"id":"c66329d84a2acf1c11296b3efc42931dd00d76'
                    'b8bfb8e5b37d43bff8fa921914","sig":"6e620802ec934fdc7580df'
                    "54a852161e9732414d0963c10de9f42b831065cf139b8e9f8aa333b42"
                    '81376d4c42b281d48e5ece4643f8a42091a4788da3a1fe116","pubke'
                    'y":"e8b4b30e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15'
                    'e67149886cf","created_at":1713722971,"tags":[["p","e8b4b3'
                    "0e67c9eabc719018435e57ae45fd0eec2f6ada428b04d15e67149886c"
                    'f"],["amount","1337000"],["relays","wss://relay.nostr.ban'
                    'd/","wss://nos.lol/","wss://relay.damus.io/"],["e","4af81'
                    "8a397daa226a85e8012197bee9ac4fd9cce85b4949334481d0c5bc573"
                    '22"]],"content":""}'
                ),
                "invoice": (
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
                "isPaid": True,
                "receivedSat": 10,
                "fees": 0,
                "completedAt": 1713300291913,
                "createdAt": 1713300266711,
            }
        )

    async def outgoing_payment_id(self, payment_id: str):
        raise NotImplementedError()

    async def payments_websocket(self):
        raise NotImplementedError()


def description_for_form(
    form_data: dict[str, str],
    description: str | None,
    description_hash: str | None,
):
    if description_hash:
        if len(description_hash) != 64:
            raise ValueError("`description_hash` must be SHA256 hexdigest (64 char)")
        try:
            _ = bytes.fromhex(description_hash)
        except ValueError as e:
            raise ValueError(
                "`description_hash` must be a valid SHA256 hexdigest (0-9a-f)"
            ) from e
        form_data["descriptionHash"] = description_hash
    elif description:
        if len(description.encode("utf-8")) > MAX_DESCRIPTION:
            # Maximum length of a BOLT-11 invoice description is 637 chars,
            # additionally Phoenixd imposes a lower 128 char limit.
            raise ValueError(f"Description is too long, max {MAX_DESCRIPTION} chars")
        else:
            form_data["description"] = description
    else:
        raise ValueError("One of `description` or `description_hash` must be set")
