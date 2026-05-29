"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health

__version__ = "0.1.0"


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="LifeHubAI",
        description="LifeHubAI API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])

    return app


app = create_app()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "LifeHubAI",
        "version": __version__,
        "status": "running",
    }
