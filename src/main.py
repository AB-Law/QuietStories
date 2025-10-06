"""
FastAPI application for the Dynamic CYOA Engine
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.api.scenarios import router as scenarios_router
from src.api.sessions import router as sessions_router

# Create FastAPI app
app = FastAPI(
    title="Dynamic CYOA Engine",
    description="Generate interactive stories from free text",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dynamic CYOA Engine",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
