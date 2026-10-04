import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, conversations, dashboard, integrations, io, leads, meetings, prospects, settings
from app.config import get_settings
from app.database.session import Base, engine
from app import models  # noqa: F401  (register models)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("age")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def create_app(create_tables: bool = True) -> FastAPI:
    s = get_settings()
    if s.environment == "production" and (s.secret_key in ("", "change-me") or len(s.secret_key) < 32):
        raise RuntimeError("SECRET_KEY must be set to a random value of at least 32 characters in production.")
    app = FastAPI(title=s.app_name, docs_url="/api/docs" if s.environment != "production" else None,
                  openapi_url="/api/openapi.json" if s.environment != "production" else None)

    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

    @app.middleware("http")
    async def security(request: Request, call_next):
        # CSRF defence for cookie sessions: state-changing requests must carry a custom header,
        # which browsers cannot send cross-site without a CORS preflight we don't allow.
        if (request.method not in SAFE_METHODS and request.url.path.startswith("/api/")
                and "authorization" not in request.headers
                and request.headers.get("x-requested-with") != "age"):
            return JSONResponse({"detail": "Missing request header."}, status_code=403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
                                    if request.url.path.startswith("/api/") and "docs" not in request.url.path
                                    else "frame-ancestors 'none'")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        errors = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        msg = "; ".join(f"{e['field']}: {e['message']}" for e in errors[:3])
        return JSONResponse({"detail": msg or "Invalid input", "errors": errors}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("unhandled error")  # stack trace stays in server logs only
        return JSONResponse({"detail": "Something went wrong. Please try again."}, status_code=500)

    for r in (auth, prospects, conversations, leads, meetings, dashboard, io, integrations, settings):
        app.include_router(r.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    if create_tables:
        Base.metadata.create_all(engine)
    return app


app = create_app(create_tables=get_settings().environment != "test" and get_settings().db_auto_create)
