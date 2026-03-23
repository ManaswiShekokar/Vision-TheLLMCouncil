"""
Page routes for serving HTML templates.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from ..config import settings, ROLE_DEFINITIONS, AVAILABLE_MODELS

router = APIRouter(tags=["pages"])

# Get the directory where templates are stored
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "roles": ROLE_DEFINITIONS,
            "models": AVAILABLE_MODELS
        }
    )


@router.get("/deliberate", response_class=HTMLResponse)
async def deliberate_page(request: Request):
    """Render the deliberation page."""
    return templates.TemplateResponse(
        "deliberate.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "roles": ROLE_DEFINITIONS,
            "models": AVAILABLE_MODELS,
            "default_models": settings.default_models
        }
    )


@router.get("/session/{session_id}", response_class=HTMLResponse)
async def session_page(request: Request, session_id: str):
    """Render the session details page."""
    return templates.TemplateResponse(
        "session.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "session_id": session_id,
            "roles": ROLE_DEFINITIONS
        }
    )


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Render the about page."""
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "app_name": settings.app_name
        }
    )
