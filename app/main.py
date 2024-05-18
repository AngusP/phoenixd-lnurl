import json
import math
import sys
from contextlib import asynccontextmanager
from typing import Annotated

import aiohttp
from fastapi import (
    APIRouter,
    BackgroundTasks,
    FastAPI,
    Path,
    Query,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import (
    JSONResponse,
    Response,
)
from fastapi.templating import Jinja2Templates
from lnurl import (
    LnurlErrorResponse,
    LnurlPayActionResponse,
)
from lnurl.types import MilliSatoshi
from loguru import logger
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .models import (
    LnurlPayNostrResponse,
    NostrNIP5Response,
    NostrZapReceipt,
    NostrZapRequest,
    PhoenixdWebsocketNotification,
)
from .phoenixd_client import (
    CreateInvoiceResponse,
    IncomingPaymentResponse,
    PhoenixdHttpClient,
    PhoenixdMockClient,
)
from .settings import PhoenixdLNURLSettings
from .setup_logging import intercept_logging

DEFAULT_ERROR_RESPONSE_MODELS: dict[int | str, dict[str, type]] = {
    400: {"model": LnurlErrorResponse},
    404: {"model": LnurlErrorResponse},
    422: {"model": LnurlErrorResponse},
    500: {"model": LnurlErrorResponse},
}
MAX_COMMENT: int = 140

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class AppError(ValueError): ...


@router.get(
    path="/lnurl",
    summary="Get a LUD-01 LNURL QR Code and LUD-16 identifier",
    description="A Tip webpage, providing a way for someone to discover your LNURL address",
    operation_id="lnurl-tip-page",
    response_class=Response,
)
async def lnurl_get_lud01(request: Request) -> Response:
    settings: PhoenixdLNURLSettings = request.app.state.settings
    return templates.TemplateResponse(
        name="lnurl-splash.html",
        context={
            "request": request,
            "username": settings.username,
            "lnurl_address": settings.lnurl_address(),
            "nostr_address": settings.user_nostr_address,
            "profile_image_url": settings.user_profile_image_url,
            "meta_description": settings.lnurl_hostname,
            "meta_author": settings.lnurl_address(),
            "encoded_lnurl": settings.lnurl_address_encoded(),
            "lnurl_qr": settings.lnurl_qr(),
            "smaller_heading": settings.is_long_username(),
        },
    )


@router.get(
    path="/lnurlp/{username}",
    summary="payRequest LUD-06",
    operation_id="lnurlp-LUD06",
    response_model=LnurlPayNostrResponse,
    responses=DEFAULT_ERROR_RESPONSE_MODELS,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
)
async def lnurl_pay_request_lud06(
    request: Request,
    username: Annotated[
        str,
        Path(
            description="username to pay",
            examples=["satoshi"],
            regex=r"^[a-z0-9-_\.]+$",
        ),
    ],
) -> LnurlPayNostrResponse | JSONResponse:
    """
    Implements [LUD-06](https://github.com/lnurl/luds/blob/luds/06.md)
    `payRequest` initial step
    """
    settings: PhoenixdLNURLSettings = request.app.state.settings
    if username != settings.username:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=LnurlErrorResponse(reason="Unknown user").dict(),
        )
    username = settings.username

    logger.info("LUD-06 payRequest for username='{username}'", username=username)
    return LnurlPayNostrResponse.parse_obj(
        dict(
            callback=str(settings.base_url() / f"lnurlp/{username}/callback"),
            minSendable=settings.min_sats_receivable * 1000,
            maxSendable=settings.max_sats_receivable * 1000,
            metadata=settings.metadata_for_payrequest(),
            comment_allowed=MAX_COMMENT,
            nostr_pubkey=settings.user_nostr_address_hex(),
            allows_nostr=settings.supports_nostr_zaps(),
        )
    )


@router.get(
    path="/.well-known/lnurlp/{username}",
    summary="payRequest LUD-16",
    operation_id="lnurlp-LUD16",
    response_model=LnurlPayNostrResponse,
    responses=DEFAULT_ERROR_RESPONSE_MODELS,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
)
async def lnurl_pay_request_lud16(
    request: Request,
    username: Annotated[
        str,
        Path(
            description="username to pay",
            examples=["satoshi"],
            regex=r"^[a-z0-9-_\.]+$",
        ),
    ],
) -> LnurlPayNostrResponse | JSONResponse:
    """
    Implements [LUD-16](https://github.com/lnurl/luds/blob/luds/16.md) `payRequest`
    initial step, using human-readable `username@host` addresses.
    """
    settings: PhoenixdLNURLSettings = request.app.state.settings
    if username != settings.username:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=LnurlErrorResponse(reason="Unknown user").dict(),
        )
    username = settings.username

    logger.info("LUD-16 payRequest for username='{username}'", username=username)
    return LnurlPayNostrResponse.parse_obj(
        dict(
            callback=str(settings.base_url() / f"lnurlp/{username}/callback"),
            minSendable=settings.min_sats_receivable * 1000,
            maxSendable=settings.max_sats_receivable * 1000,
            metadata=settings.metadata_for_payrequest(),
            comment_allowed=MAX_COMMENT,
            nostr_pubkey=settings.user_nostr_address_hex(),
            allows_nostr=settings.supports_nostr_zaps(),
        )
    )


@router.get(
    path="/lnurlp/{username}/callback",
    summary="payRequest callback LUD-06",
    operation_id="lnurlp-LUD06 callback",
    response_model=LnurlPayActionResponse,
    responses=DEFAULT_ERROR_RESPONSE_MODELS,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
)
async def lnurl_pay_request_callback_lud06(
    request: Request,
    username: Annotated[
        str,
        Path(
            description="username to pay",
            examples=["satoshi"],
            regex=r"^[a-z0-9-_\.]+$",
        ),
    ],
    amount: Annotated[
        MilliSatoshi,
        Query(
            description="amount to pay, in millisatoshis (mSat)",
            examples=[1337000],
        ),
    ],
    comment: Annotated[
        str | None,
        Query(
            description="(Optional) sending wallet can provide a comment for this payment",
            examples=["HFSP"],
        ),
    ] = None,
    nostr: Annotated[
        str | None,
        Query(
            description="(Optional) for Nostr zaps, provides kind `9734` Nostr event",
        ),
    ] = None,
) -> LnurlPayActionResponse | JSONResponse:
    settings: PhoenixdLNURLSettings = request.app.state.settings
    if username != settings.username:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=LnurlErrorResponse(reason="Unknown user").dict(),
        )
    username = settings.username
    zap_request = None

    if comment is not None:
        logger.debug("Raw comment: '{comment}'", comment=comment)
    if nostr is not None:
        logger.debug("Raw nostr zapRequest {raw_nostr}", raw_nostr=nostr)
        if settings.supports_nostr_zaps():
            try:
                zap_request = NostrZapRequest.parse_raw(nostr)
            except ValidationError:
                logger.warning(
                    "Couldn't decode ?nostr= zap request parameter, ignoring"
                )
        else:
            logger.debug(
                (
                    "No Nostr info configured for {user} so ignoring zap "
                    "request and using plain LNURL"
                ),
                user=username,
            )

    # TODO check compatibility of conversion to sats, some wallets
    # may not like the invoice amount not matching?
    amount_sat = math.ceil(amount / 1000)
    logger.info(
        (
            "LUD-06 payRequestCallback for username='{username}' "
            "sat={amount_sat} (mSat={amount}) (nostr={is_nostr})"
        ),
        username=username,
        amount_sat=amount_sat,
        amount=amount,
        is_nostr="yes" if zap_request is not None else "no",
    )

    if amount_sat < settings.min_sats_receivable:
        logger.warning(
            "LUD-06 payRequestCallback with too-low amount {amount_sat} sats",
            amount_sat=amount_sat,
        )
        raise AppError(
            f"Amount is too low, minimum is {settings.min_sats_receivable} sats"
        )

    if amount_sat > settings.max_sats_receivable:
        logger.warning(
            "LUD-06 payRequestCallback with too-high amount {amount_sat} sats",
            amount_sat=amount_sat,
        )
        raise AppError(
            f"Amount is too high, maximum is {settings.max_sats_receivable} sats"
        )

    if zap_request:
        try:
            zap_request.is_valid(
                amount_msat=amount,
                expected_nostr_pubkey=settings.user_nostr_address_hex(),
            )
        except ValueError as e:
            # If we got something that looked like a Zap Request but couldn't
            # handle it we return an error rather than continue with plain LNURL
            raise AppError(f"Invalid NIP-57 Zap Request event: {e}") from e

    invoice_description, invoice_description_hash = None, None
    if zap_request:
        invoice_description_hash = zap_request.invoice_description_hash()
    else:
        invoice_description = settings.metadata_hash()

    # Passed to phoenixd as `externalId` so payments can be looked up against
    # the Zap request's event ID or just LNURL
    invoice_reference_id = (
        f"zap-{zap_request.nostr_id}" if zap_request else f"lnurl-{invoice_description}"
    )
    # TODO save/log invoice_reference_ids?

    phoenixd_client: PhoenixdHttpClient = request.app.state.phoenixd_client

    invoice: CreateInvoiceResponse = await phoenixd_client.createinvoice(
        amount_sat=amount_sat,
        description=invoice_description,
        description_hash=invoice_description_hash,
        external_id=invoice_reference_id,
    )
    return LnurlPayActionResponse.parse_obj(
        dict(
            pr=invoice.serialized,
            success_action={
                "tag": "message",
                "message": f"Thanks for zapping {username}",
            },
            routes=[],
        )
    )


@router.get(
    path="/.well-known/nostr.json",
    summary="NIP-5 Nostr Identifier",
    operation_id="nostr-NIP5",
    response_model=NostrNIP5Response,
    responses=DEFAULT_ERROR_RESPONSE_MODELS,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
)
async def nostr_nip5_request(request: Request) -> NostrNIP5Response:
    settings: PhoenixdLNURLSettings = request.app.state.settings
    if not settings.user_nostr_address:
        raise StarletteHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    nostr_address_hex = settings.user_nostr_address_hex()
    nostr_relays = settings.nostr_relays
    if nostr_address_hex is None or not nostr_relays:
        raise StarletteHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
    return NostrNIP5Response(
        names={settings.username: nostr_address_hex},
        relays={nostr_address_hex: nostr_relays},
    )


@router.post(
    path="/phoenixd-webhook",
    summary="INTERNAL - Handler for phoenixd webhook notifications",
    operation_id="phoenixd-webhook",
)
async def phoenixd_webhook_handler(
    request: Request,
    hook: PhoenixdWebsocketNotification,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    settings: PhoenixdLNURLSettings = request.app.state.settings
    session: aiohttp.ClientSession = request.app.state.client_session
    logger.debug("Webhook from phoenixd: {hook}", hook=hook)

    if hook.external_id and not hook.external_id.startswith("zap"):
        # We only need to handle paid Zaps, ignore everything else
        return JSONResponse(content={"status": "ok"})

    if (
        nostr_pubkey := settings.user_nostr_address_hex()
    ) is None or not settings.supports_nostr_zaps():
        # Should never happen, in theory 😉
        raise ValueError("Cannot handle zaps without nostr support")

    # Get the invoice from phoenixd
    paid_invoice: IncomingPaymentResponse = (
        await request.app.state.phoenixd_client.incoming_payment_hash(
            payment_hash=hook.payment_hash
        )
    )
    if not paid_invoice.is_paid:
        # Should never happen, in theory 😉
        return JSONResponse(content={"status": "ok"})

    # TODO(angus) when using description hash, there is no description!
    original_zap_request = NostrZapRequest.parse_raw(paid_invoice.description or "")
    logger.debug("Parsed zap request: {zap}", zap=original_zap_request)

    zap_receipt = NostrZapReceipt.from_zap_request(
        zap_request=original_zap_request,
        paid_invoice=paid_invoice,
        nostr_pubkey=nostr_pubkey,
        nostr_private_key=settings.nostr_private_key(),
    )
    logger.debug("Created zap receipt: {receipt}", receipt=zap_receipt)

    # Send the Zap Receipt to the requester's specified relays
    receipt_relays = original_zap_request.receipt_relays()

    # Publish the Zap receipt event as a background task
    if not settings.is_test:
        background_tasks.add_task(
            background_nostr_publish,
            session,
            zap_receipt,
            receipt_relays,
        )
    return JSONResponse(
        content={
            "status": "ok",
            "receipt": zap_receipt.dict(by_alias=True, exclude_unset=False),
        }
    )


async def background_nostr_publish(
    session: aiohttp.ClientSession,
    event: NostrZapReceipt,
    relays: list[str],
):
    payload = [
        "EVENT",
        event.dict(
            by_alias=True,
            exclude_unset=False,
            exclude_none=True,
        ),
    ]
    # TODO be less dumb with websocket handling
    for relay_url in relays:
        try:
            async with session.ws_connect(relay_url, timeout=5) as ws:
                logger.info("Connect {relay_url}", relay_url=relay_url)
                await ws.send_json(data=payload)
                async for msg in ws:
                    logger.debug(msg.data)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        response = json.loads(msg.data)
                        logger.info(
                            "Response from {relay_url}: {resp}",
                            relay_url=relay_url,
                            resp=response,
                        )
                    break
        except aiohttp.ClientError as e:
            logger.warning(e)
    logger.info("Zap receipt published")


async def base_exception_handler(
    request: Request,
    exc: Exception,
    status_code: int = 400,
    include_detail: bool = False,
) -> JSONResponse:
    logger.exception(exc)
    if include_detail and request.app.state.settings.debug:
        reason = f"<{exc.__class__.__name__}>: {str(exc)}"
    elif include_detail:
        reason = str(exc).strip() or "Error"
    else:
        reason = "Internal Server Error"
    return JSONResponse(
        content=LnurlErrorResponse(reason=reason).dict(),
        status_code=status_code,
    )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return await base_exception_handler(request, exc, include_detail=True)

    @app.exception_handler(ValidationError)
    async def model_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            include_detail=True,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=exc.status_code,
            include_detail=True,
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=status.HTTP_400_BAD_REQUEST,
            include_detail=True,
        )

    @app.exception_handler(TimeoutError)
    async def timeout_handler(request: Request, exc: TimeoutError) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            include_detail=request.app.debug,
        )

    @app.exception_handler(Exception)
    async def default_handler(request: Request, exc: Exception) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            include_detail=request.app.debug,
        )


def configure_logging(loglevel: str = "INFO", backtrace: bool = False):
    logger.remove()
    intercept_logging()
    logger.add(
        sys.stdout,
        colorize=True,
        level=loglevel,
        format=(
            "<fg #FF9900>{time:%Y-%m-%d:%H:%m:%S}</fg #FF9900>  "
            "<level>{level:9}  {message}</level>"
        ),
        backtrace=backtrace,
        diagnose=backtrace,
    )


def app_factory() -> FastAPI:
    # Settings are auto-loaded from a `.env` file
    settings: PhoenixdLNURLSettings = PhoenixdLNURLSettings()  # type: ignore
    if settings.is_test:
        settings = PhoenixdLNURLSettings(_env_file="test.env")  # type: ignore

    configure_logging(settings.log_level, settings.debug)
    logger.debug("Loaded settings: {settings}", settings=settings)

    if not settings.debug:
        sys.tracebacklimit = 0

    @asynccontextmanager
    async def lifespan_context(app: FastAPI):
        """
        Use a shared aiohttp ClientSession for the lifetime of the ASGI app
        """
        app.state.client_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=10.0,
                connect=2.0,
            )
        )
        if settings.is_test:
            app.state.phoenixd_client = PhoenixdMockClient(
                phoenixd_url=settings.phoenixd_url.get_secret_value(),
            )
        else:
            app.state.phoenixd_client = PhoenixdHttpClient(
                session=app.state.client_session,
                phoenixd_url=settings.phoenixd_url.get_secret_value(),
            )
        yield
        await app.state.client_session.close()

    app = FastAPI(
        debug=settings.debug,
        title="phoenixd-lnurl",
        version="0.1.0",
        license_info={
            "name": "BSD-2-Clause",
            "url": (
                "https://raw.githubusercontent.com/AngusP/phoenixd-lnurl/"
                "master/LICENSE.BSD-2-Clause"
            ),
        },
        lifespan=lifespan_context,
        logger=logger,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.include_router(router)
    register_exception_handlers(app)
    return app
