import hmac
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.financial_scenario import router as financial_scenario_router
from app.api.intelligence import router as intelligence_router
from app.api.profile_intelligence import router as profile_intelligence_router
from app.api.scholarships_v2 import router as scholarships_v2_router
from app.api.v1.auth import router as auth_router
from app.api.v1.router import router
from app.api.v1.workspace import router as workspace_router
from app.core.config import Settings
from app.db.session import build_engine
from app.schemas.catalog import ErrorResponseDTO

logger = logging.getLogger("atlas")


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    settings = settings or Settings()
    db_engine = engine if engine is not None else build_engine(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # No schema creation or migration on startup. Liveness is independent of PostgreSQL.
        try:
            yield
        finally:
            if engine is None:
                db_engine.dispose()

    app = FastAPI(
        title="Atlas API",
        version="0.3.0",
        lifespan=lifespan,
        responses={code: {"model": ErrorResponseDTO} for code in [404, 405, 422, 500, 503]},
    )
    app.state.settings = settings
    app.state.engine = db_engine
    if settings.staging_demo:
        from app.services.staging_mail import StagingMailbox

        app.state.staging_mailbox = StagingMailbox()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Accept", "Content-Type", "X-Atlas-CSRF"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    @app.middleware("http")
    async def private_security(request: Request, call_next):
        path = request.url.path
        safe = request.method in {"GET", "HEAD", "OPTIONS"}
        private = path.startswith(
            ("/api/v1/auth", "/api/v1/me", "/api/v1/advisor", "/api/v1/staging-mail")
        )
        if settings.staging_demo:
            public_health = path == "/api/v1/health" and request.method in {"GET", "HEAD"}
            if not public_health and not hmac.compare_digest(
                request.headers.get("X-Atlas-Staging-Key", "").encode(),
                settings.staging_transport_key.get_secret_value().encode(),
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "forbidden",
                            "message": "Trusted demo transport required.",
                        }
                    },
                    headers={"Cache-Control": "no-store"},
                )
            if not settings.staging_database_writes_enabled and (
                path.startswith(("/api/v1/auth", "/api/v1/me", "/api/v2/me"))
                or (not safe and not path.startswith("/api/v1/staging-mail/"))
            ):
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "not_initialized",
                            "message": "Demo account actions await separately approved initialization.",
                        }
                    },
                    headers={"Cache-Control": "no-store"},
                )
            if path == "/api/v1/auth/register" and not settings.staging_signup_enabled:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {"code": "forbidden", "message": "Demo registration is closed."}
                    },
                    headers={"Cache-Control": "no-store"},
                )
        if private and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get(
                "origin"
            ) not in settings.cors_origins or not request.headers.get("X-Atlas-CSRF"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "forbidden",
                            "message": "A trusted origin and CSRF header are required.",
                        }
                    },
                )
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 65536:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "payload_too_large",
                                "message": "Request exceeds 64 KiB.",
                            }
                        },
                    )
                body.extend(chunk)
            request._body = bytes(body)
            if settings.staging_demo and path in {
                "/api/v1/auth/register",
                "/api/v1/auth/login",
                "/api/v1/auth/forgot-password",
                "/api/v1/auth/resend-verification",
            }:
                try:
                    email = json.loads(body).get("email", "").strip().lower()
                except (ValueError, AttributeError, TypeError):
                    email = ""
                if email not in settings.staging_synthetic_emails:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": {
                                "code": "forbidden",
                                "message": "Only approved synthetic accounts are available.",
                            }
                        },
                        headers={"Cache-Control": "no-store"},
                    )
        response = await call_next(request)
        if private or request.url.path.startswith("/api/v2/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        codes = {
            400: "invalid_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
            503: "service_unavailable",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": codes.get(exc.status_code, "request_error"),
                    "message": str(exc.detail),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Never include rejected values, credentials, internal exception context, or stack traces.
        fields = [
            {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request parameters",
                    "fields": fields,
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error("Database request failed (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "service_unavailable",
                    "message": "Catalog database is unavailable. Please try again.",
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Unexpected request failure (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "The request could not be completed.",
                }
            },
        )

    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    app.include_router(scholarships_v2_router)
    app.include_router(intelligence_router)
    app.include_router(profile_intelligence_router)
    app.include_router(financial_scenario_router)
    if settings.staging_demo:
        from app.api.staging import router as staging_router

        app.include_router(staging_router)
    if settings.experimental_foundation:
        from app.experimental.router import router as foundation_router

        app.include_router(foundation_router)
    if settings.experimental_journey:
        from app.journey.router import router as journey_router

        app.include_router(journey_router)
    if settings.experimental_advisor:
        from app.advisor.router import Quota
        from app.advisor.router import router as advisor_router

        app.state.advisor_quota = Quota()
        app.include_router(advisor_router)
    return app


app = create_app()
