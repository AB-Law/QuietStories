"""
FastAPI application for the Dynamic CYOA Engine
"""

import os
import time
import uuid
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.api.optimization import router as optimization_router
from backend.api.prompts import router as prompts_router
from backend.api.scenarios import router as scenarios_router
from backend.api.sessions import router as sessions_router
from backend.api.settings import router as settings_router
from backend.config import settings
from backend.utils.logger import LogLevel, get_logger, setup_logging

# Initialize logging for Grafana/Loki integration
# Get log level from environment variable, default to INFO
log_level_raw = os.getenv("LOG_LEVEL", "INFO").upper()
log_level: LogLevel = log_level_raw if log_level_raw in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO"  # type: ignore
log_file = os.getenv("LOG_FILE")  # Optional log file

# Configure for centralized logging (disable console spam in production)
enable_console_logging = os.getenv("ENABLE_CONSOLE_LOGS", "true").lower() == "true"
enable_colors = enable_console_logging  # Only colorize if console logging is enabled

setup_logging(
    level=log_level,
    log_file=log_file,
    enable_colors=enable_colors,
    include_timestamp=True,
    enable_file_logging=True,  # Always enable file logging for Loki
    enable_console_logging=enable_console_logging,
)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dynamic CYOA Engine",
    description="Generate interactive stories from free text",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

logger.info("FastAPI application initialized")
logger.info(f"Log level: {log_level}")
logger.info(f"Model provider: {settings.model_provider}")
logger.info(f"Model name: {settings.model_name}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all HTTP requests and responses for Grafana monitoring"""

    # Generate request ID for correlation
    request_id = str(uuid.uuid4())[:8]

    # Start timing
    start_time = time.time()

    # Extract client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    content_type = request.headers.get("content-type", "")

    # Read request body for logging (only for non-GET requests)
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                if "application/json" in content_type:
                    import json

                    try:
                        request_body = json.loads(body.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_body = {
                            "body_size": len(body),
                            "content_type": content_type,
                        }
                else:
                    request_body = {
                        "body_size": len(body),
                        "content_type": content_type,
                    }
        except Exception as e:
            request_body = {"error_reading_body": str(e)}

    # Log request start
    logger.info(
        f"[API] Request started: {request.method} {request.url.path}",
        extra={
            "component": "API",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "content_type": content_type,
            "query_params": (
                dict(request.query_params) if request.query_params else None
            ),
            "request_body": request_body,
        },
    )

    # Store request_id in request state for use in endpoints
    request.state.request_id = request_id

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Extract response details
        response_details = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type", ""),
        }

        # For certain endpoints, log response body (be careful with large responses)
        if request.url.path.startswith("/sessions") or "error" in str(
            response.status_code
        ):
            try:
                # This is tricky with streaming responses, so we'll be selective
                if response.status_code >= 400:
                    response_details["error_response"] = True
            except Exception:
                pass

        # Log request completion
        logger.info(
            f"[API] Request completed: {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "component": "API",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "response_details": response_details,
            },
        )

        return response

    except Exception as e:
        # Calculate duration for error case
        duration_ms = (time.time() - start_time) * 1000

        # Log error
        logger.error(
            f"[API] Request failed: {request.method} {request.url.path} -> ERROR ({duration_ms:.2f}ms): {str(e)}",
            extra={
                "component": "API",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )

        # Re-raise the exception
        raise


# Include routers
app.include_router(scenarios_router, prefix="/scenarios", tags=["scenarios"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
app.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])
app.include_router(optimization_router, prefix="/optimization", tags=["optimization"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 60)

    # Initialize database
    from backend.db.manager import DatabaseManager

    db = DatabaseManager(settings.database_path)
    logger.info(f"✓ Database initialized: {settings.database_path}")

    # Log configuration
    logger.info(f"Configuration:")
    logger.info(f"  - Provider: {settings.model_provider}")
    logger.info(f"  - Model: {settings.model_name}")
    logger.info(f"  - Database: {settings.database_path}")
    logger.info(f"  - Debug: {settings.debug}")
    logger.info("=" * 60)


@app.get("/")
async def root():
    """Root endpoint"""
    logger.debug("Root endpoint called")
    return {
        "message": "Dynamic CYOA Engine",
        "version": "0.1.0",
        "status": "running",
        "log_level": log_level,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check endpoint called")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=log_level.lower(),
    )
# test comment
# another test
