"""
Main FastAPI application entry point.
"""
import logging
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import audits, files, reports, customers, tariffs


def _install_request_id_default() -> None:
    """Ensure non-request logs still have a request_id field."""
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return record

    logging.setLogRecordFactory(record_factory)


def _parse_cors_origins(raw_value: str) -> list[str]:
    """
    Parse CORS origins from either:
    - Comma-separated string: "https://a.com,https://b.com"
    - JSON-like list string: ["https://a.com", "https://b.com"]
    """
    value = (raw_value or "").strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [origin.strip().strip("'\"") for origin in inner.split(",") if origin.strip().strip("'\"")]
    return [origin.strip() for origin in value.split(",") if origin.strip()]

# Configure logging
_install_request_id_default()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
)

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        
        return response

app = FastAPI(
    title="3PL Links Freight Audit Platform",
    description="Freight audit and analytics platform",
    version="1.0.0"
)

# Request ID middleware (must be added first)
app.add_middleware(RequestIDMiddleware)

# CORS middleware with enhanced configuration
cors_origins = _parse_cors_origins(
    os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
    max_age=3600,
)

# Include routers
app.include_router(customers.router, prefix="/api/customers", tags=["customers"])
app.include_router(audits.router, prefix="/api/audits", tags=["audits"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(tariffs.router, prefix="/api/tariffs", tags=["tariffs"])


@app.get("/")
async def root():
    return {"message": "3PL Links Freight Audit Platform API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

