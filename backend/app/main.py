"""
Main FastAPI application entry point.
"""
import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api import audits, files, reports, customers, tariffs
from app.db.database import engine, Base

# Configure logging
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

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="3PL Links Freight Audit Platform",
    description="Freight audit and analytics platform",
    version="1.0.0"
)

# Request ID middleware (must be added first)
app.add_middleware(RequestIDMiddleware)

# CORS middleware with enhanced configuration
import os
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

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


