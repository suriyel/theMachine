"""Web UI routes - HTML pages for search and login."""

import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.query.dependencies import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_MAX_AGE,
    create_session,
    destroy_session,
    get_db,
    get_session,
    require_auth,
)
from src.query.language_filter import LanguageFilter
from src.shared.models.api_key import APIKey, KeyStatus


router = APIRouter()

# Setup Jinja2 environment
template_dir = __file__.replace("api/web.py", "templates")
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(["html", "xml"]),
)

# Add url_for to template globals
jinja_env.globals["url_for"] = lambda *args, **kwargs: f"/static{kwargs.get('path', '')}"

# Template cache for simple rendering
_templates_cache = {}


def render_template(template_name: str, **context) -> str:
    """Render a template with given context."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


SUPPORTED_LANGUAGES = ["java", "python", "typescript", "javascript", "c", "cpp"]
_language_filter = LanguageFilter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """Display login page."""
    # Check if already authenticated
    if get_session(request):
        return RedirectResponse(url="/search", status_code=302)

    return render_template("login.html", error=error)


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    api_key: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle login form submission."""
    # Check if already authenticated
    if get_session(request):
        return RedirectResponse(url="/search", status_code=302)

    # Validate API key
    if not api_key or not api_key.strip():
        return HTMLResponse(
            content=await login_page(request, error="API key is required"),
            status_code=401,
        )

    # Hash and verify the API key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    stmt = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.status == KeyStatus.ACTIVE
    )
    result = await db.execute(stmt)
    api_key_record = result.scalar_one_or_none()

    if not api_key_record:
        return HTMLResponse(
            content=await login_page(request, error="Invalid API key"),
            status_code=401,
        )

    # Create session
    session_token = create_session(api_key_record.id, api_key_record.name)

    # Set session cookie and redirect
    response = RedirectResponse(url="/search", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: Optional[str] = None,
    lang: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Display search page."""
    # Require authentication
    try:
        session_data = require_auth(request)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    from src.query.dependencies import get_query_handler

    results = None
    error = None
    initial = True

    # Validate language filter
    if lang:
        try:
            lang = _language_filter.validate(lang)
        except ValueError as e:
            error = str(e)
            lang = None

    # Execute search if query provided
    if q and q.strip():
        initial = False
        query = q.strip()

        try:
            handler = await get_query_handler()

            # Build query params
            query_params = {
                "query_text": query,
                "query_type": "natural_language",
                "top_k": 3,
            }

            if lang:
                query_params["language_filter"] = lang

            result = await handler.handle_query(**query_params)

            if result.get("results"):
                results = result["results"]

        except Exception as e:
            error = f"Search error: {str(e)}"

    return render_template(
        "search.html",
        query=q,
        language_filter=lang,
        results=results,
        error=error,
        initial=initial,
    )


@router.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    destroy_session(request)

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME)

    return response
