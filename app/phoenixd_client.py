from abc import (
    ABC,
    abstractmethod,
)

import aiohttp
from loguru import logger
from pydantic import (
    BaseModel,
    Field,
)
from yarl import URL


class ChannelInfo(BaseModel):
    state: str
    channel_id: str = Field(alias="channelId")
    balance_dat: int = Field(alias="balanceSat", ge=0)
    inbound_liquidity_sat: int = Field(alias="inboundLiquiditySat", ge=0)
    capacity_sat: int = Field(alias="capacitySat", ge=0)
    funding_tx_id: str = Field(alias="fundingTxId")


class GetInfoResponse(BaseModel):
    node_id: str = Field(alias="nodeId")
    channels: list[ChannelInfo]
    chain: str
    version: str


class GetBalanceResponse(BaseModel):
    balance_sat: int = Field(alias="balanceSat", ge=0)
    fee_credit_sat: int = Field(alias="feeCreditSat", ge=0)


class ListChannelsResponse(BaseModel):
    channels: list[dict]


class CreateInvoiceResponse(BaseModel):
    amount_sat: int = Field(alias="amountSat", ge=0)
    payment_hash: str = Field(alias="paymentHash")
    serialized: str


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
        description: str | bytes,
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
    async def incoming_payments_external_id(self, external_id: str): ...

    @abstractmethod
    async def incoming_payment_hash(self, hash: str | bytes): ...

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
        description: str | bytes,
        external_id: str | None = None,
    ) -> CreateInvoiceResponse:
        form_data = {
            "amountSat": amount_sat,
            "description": description,
        }
        if external_id is not None:
            form_data["externalId"] = external_id
        async with self.session.post(
            self.baseurl / "createinvoice",
            data=form_data,
        ) as response:
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

    async def incoming_payments_external_id(self, external_id: str):
        raise NotImplementedError()

    async def incoming_payment_hash(self, hash: str | bytes):
        raise NotImplementedError()

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
        description: str | bytes,
        external_id: str | None = None,
    ) -> CreateInvoiceResponse:
        # Static mock invoice
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

    async def incoming_payments_external_id(self, external_id: str):
        raise NotImplementedError()

    async def incoming_payment_hash(self, hash: str | bytes):
        raise NotImplementedError()

    async def outgoing_payment_id(self, payment_id: str):
        raise NotImplementedError()

    async def payments_websocket(self):
        raise NotImplementedError()
