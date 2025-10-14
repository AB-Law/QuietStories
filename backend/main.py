"""
FastAPI application for the Dynamic CYOA Engine
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api.optimization import router as optimization_router
from backend.api.prompts import router as prompts_router
from backend.api.scenarios import router as scenarios_router
from backend.api.sessions import router as sessions_router
from backend.api.settings import router as settings_router
from backend.config import settings
from backend.utils.logger import LogLevel, get_logger, setup_logging

# Initialize logging
# Get log level from environment variable, default to INFO
log_level_raw = os.getenv("LOG_LEVEL", "INFO").upper()
log_level: LogLevel = log_level_raw if log_level_raw in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO"  # type: ignore
log_file = os.getenv("LOG_FILE")  # Optional log file

setup_logging(
    level=log_level, log_file=log_file, enable_colors=True, include_timestamp=True
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
