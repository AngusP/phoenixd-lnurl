import math
import sys
from contextlib import asynccontextmanager
from typing import Annotated

import aiohttp
from fastapi import (
    APIRouter,
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
    LnurlPayResponse,
)
from loguru import logger
from pydantic import PositiveInt
from starlette.exceptions import HTTPException as StarletteHTTPException

from .phoenixd_client import (
    CreateInvoiceResponse,
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

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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
    response_model=LnurlPayResponse,
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
) -> LnurlPayResponse | JSONResponse:
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
    return LnurlPayResponse.parse_obj(
        dict(
            callback=str(settings.base_url() / f"lnurlp/{username}/callback"),
            minSendable=settings.min_sats_receivable * 1000,
            maxSendable=settings.max_sats_receivable * 1000,
            metadata=settings.metadata_for_payrequest(),
        )
    )


@router.get(
    path="/.well-known/lnurlp/{username}",
    summary="payRequest LUD-16",
    operation_id="lnurlp-LUD16",
    response_model=LnurlPayResponse,
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
) -> LnurlPayResponse | JSONResponse:
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
    return LnurlPayResponse.parse_obj(
        dict(
            callback=str(settings.base_url() / f"lnurlp/{username}/callback"),
            minSendable=settings.min_sats_receivable * 1000,
            maxSendable=settings.max_sats_receivable * 1000,
            metadata=settings.metadata_for_payrequest(),
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
        PositiveInt,
        Query(
            description="amount to pay, in millisatoshis (mSat)",
            examples=[1337000],
        ),
    ],
) -> LnurlPayActionResponse | JSONResponse:
    settings: PhoenixdLNURLSettings = request.app.state.settings
    if username != settings.username:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=LnurlErrorResponse(reason="Unknown user").dict(),
        )
    username = settings.username

    # TODO check compatibility of conversion to sats, some wallets
    # may not like the invoice amount not matching?
    amount_sat = math.ceil(amount / 1000)
    logger.info(
        "LUD-06 payRequestCallback for username='{username}' sat={amount_sat} (mSat={amount})",
        username=username,
        amount_sat=amount_sat,
        amount=amount,
    )

    if amount_sat < settings.min_sats_receivable:
        logger.warning(
            "LUD-06 payRequestCallback with too-low amount {amount_sat} sats",
            amount_sat=amount_sat,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=LnurlErrorResponse(
                reason=f"Amount is too low, minimum is {settings.min_sats_receivable} sats"
            ).dict(),
        )

    if amount_sat > settings.max_sats_receivable:
        logger.warning(
            "LUD-06 payRequestCallback with too-high amount {amount_sat} sats",
            amount_sat=amount_sat,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=LnurlErrorResponse(
                reason=f"Amount is too high, maximum is {settings.max_sats_receivable} sats"
            ).dict(),
        )

    invoice: CreateInvoiceResponse = (
        await request.app.state.phoenixd_client.createinvoice(
            amount_sat=amount_sat,
            description=settings.metadata_hash(),
            external_id=settings.metadata_hash(),
        )
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


async def base_exception_handler(
    request: Request,
    exc: Exception,
    status_code: int = 400,
    include_detail: bool = False,
) -> JSONResponse:
    if include_detail:
        reason = f"{exc.__class__.__name__} {str(exc)}"
    else:
        reason = "Internal Server Error"
    return JSONResponse(
        content=LnurlErrorResponse(reason=reason).dict(),
        status_code=status_code,
    )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return await base_exception_handler(request, exc, include_detail=True)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: Exception) -> JSONResponse:
        return await base_exception_handler(request, exc, include_detail=True)

    @app.exception_handler(TimeoutError)
    async def timeout_handler(request: Request, exc: Exception) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=500,
            include_detail=request.app.debug,
        )

    @app.exception_handler(Exception)
    async def default_handler(request: Request, exc: Exception) -> JSONResponse:
        return await base_exception_handler(
            request,
            exc,
            status_code=500,
            include_detail=request.app.debug,
        )


def configure_logging(loglevel: str = "INFO"):
    logger.remove()
    intercept_logging()
    logger.add(
        sys.stdout,
        colorize=True,
        level=loglevel,
        format="<fg #FF9900>{time:%Y-%m-%d:%H:%m:%S}</fg #FF9900>  <level>{level:9}  {message}</level>",
    )


def app_factory() -> FastAPI:
    # Settings are auto-loaded from a `.env` file
    settings: PhoenixdLNURLSettings = PhoenixdLNURLSettings()  # type: ignore
    if settings.is_test:
        settings = PhoenixdLNURLSettings(_env_file="test.env")  # type: ignore

    configure_logging(settings.log_level)
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
            "url": "https://raw.githubusercontent.com/AngusP/phoenixd-lnurl/master/LICENSE.BSD-2-Clause",
        },
        lifespan=lifespan_context,
        logger=logger,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(router)
    register_exception_handlers(app)
    return app
