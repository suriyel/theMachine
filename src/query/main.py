"""FastAPI application entry point for Query Service."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.query.api.v1.router import api_router
from src.query.api.web import router as web_router
from src.query.config import settings
from src.shared.db.session import init_db
from src.shared.clients import init_clients, close_clients


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    await init_db()
    await init_clients()
    yield
    # Shutdown
    await close_clients()


app = FastAPI(
    title="Code Context Retrieval",
    description="Retrieve relevant code context from indexed Git repositories",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include Web UI routes
app.include_router(web_router)

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
