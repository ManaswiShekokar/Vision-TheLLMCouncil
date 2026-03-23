"""
LLM Council - Main FastAPI Application

A multi-LLM collaborative reasoning system with role-based responses.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import api_router, pages_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Check for API key
    if not settings.openrouter_api_key:
        logger.warning(
            "OPENROUTER_API_KEY not set! "
            "Set it in .env file or environment variable."
        )
    
    yield
    
    logger.info("Shutting down LLM Council")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    A multi-LLM collaborative reasoning system that implements:
    
    - **Role-based reasoning**: Multiple LLMs with different perspectives
    - **Anonymous peer review**: Unbiased evaluation of responses
    - **Multi-round deliberation**: Iterative improvement
    - **Weighted consensus scoring**: Merit-based synthesis
    - **Verifier validation**: Error and hallucination detection
    - **Chairman synthesis**: Authoritative final answer
    
    Simulates an expert committee solving problems together.
    """,
    version=settings.app_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(BASE_DIR, "app", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include routers
app.include_router(api_router)
app.include_router(pages_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
