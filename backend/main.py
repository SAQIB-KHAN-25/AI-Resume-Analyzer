import os
import logging
import time
import uuid
from dotenv import load_dotenv

# Load .env before importing modules that read environment variables at import time.
load_dotenv()

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .routers import (
    auth_routes,
    ai_routes,
    analysis_routes,
    profile_routes,
)
from .database import connect_to_mongo, close_mongo_connection, get_database

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "development").lower()
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

app = FastAPI(
    title="AI Resume Analyzer API",
    description="Backend API for AI-powered resume analysis and job matching",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; form-action 'self'"
        response.headers["X-Request-ID"] = request.state.request_id
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(process_ms)
        logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, process_ms)
        return response


raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
allow_origin_regex = os.getenv(
    "CORS_ALLOWED_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1)(:\\d+)?$"
)
raw_trusted_hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1")
trusted_hosts = [host.strip() for host in raw_trusted_hosts.split(",") if host.strip()]

app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize database connection on startup
    """
    logger.info("Starting AI Resume Analyzer API...")
    await connect_to_mongo()
    logger.info("✓ Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Close database connection on shutdown
    """
    logger.info("Shutting down AI Resume Analyzer API...")
    await close_mongo_connection()
    logger.info("✓ Application shutdown complete")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "n/a")
    detail = exc.detail if isinstance(exc.detail, (dict, list, str)) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "request_id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "n/a")
    logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
    detail = "Internal server error" if APP_ENV == "production" else str(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": request_id},
    )


app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(analysis_routes.router, prefix="/api", tags=["Analysis Pipeline"])
app.include_router(profile_routes.router, prefix="/api", tags=["User Profile"])
app.include_router(ai_routes.router, prefix="/api", tags=["AI Features"])


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to AI Resume Analyzer API",
        "version": APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    db_status = "connected" if get_database() is not None else "disconnected"
    return {
        "status": "healthy",
        "database": db_status,
        "version": APP_VERSION,
        "environment": APP_ENV
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
