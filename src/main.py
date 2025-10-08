"""
FastAPI application for the Dynamic CYOA Engine
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.api.scenarios import router as scenarios_router
from src.api.sessions import router as sessions_router
from src.api.prompts import router as prompts_router
from src.utils.logger import setup_logging, get_logger

# Initialize logging
# Get log level from environment variable, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_file = os.getenv("LOG_FILE")  # Optional log file

setup_logging(
    level=log_level,
    log_file=log_file,
    enable_colors=True,
    include_timestamp=True
)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dynamic CYOA Engine",
    description="Generate interactive stories from free text",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
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


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("="*60)
    logger.info("APPLICATION STARTUP")
    logger.info("="*60)
    
    # Initialize database
    from src.db.manager import DatabaseManager
    db = DatabaseManager(settings.database_path)
    logger.info(f"✓ Database initialized: {settings.database_path}")
    
    # Log configuration
    logger.info(f"Configuration:")
    logger.info(f"  - Provider: {settings.model_provider}")
    logger.info(f"  - Model: {settings.model_name}")
    logger.info(f"  - Database: {settings.database_path}")
    logger.info(f"  - Debug: {settings.debug}")
    logger.info("="*60)


@app.get("/")
async def root():
    """Root endpoint"""
    logger.debug("Root endpoint called")
    return {
        "message": "Dynamic CYOA Engine",
        "version": "0.1.0",
        "status": "running",
        "log_level": log_level
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
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=log_level.lower()
    )
