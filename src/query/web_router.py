"""WebRouter — SSR web interface for code search and repository registration."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.query.highlighter import CodeHighlighter
from src.query.exceptions import RetrievalError
from src.shared.exceptions import ConflictError, ValidationError
from src.shared.services.repo_manager import RepoManager

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Supported languages for checkbox filters (CON-001)
_SUPPORTED_LANGUAGES = ["python", "java", "javascript", "typescript", "c", "c++"]


class WebRouter:
    """Server-side rendered web interface for code search."""

    def __init__(self) -> None:
        self._templates = Jinja2Templates(directory=_TEMPLATES_DIR)
        self._highlighter = CodeHighlighter()
        self._router = APIRouter()
        self._register_routes()

    @property
    def router(self) -> APIRouter:
        return self._router

    def _register_routes(self) -> None:
        self._router.add_api_route("/", self.search_page, methods=["GET"], response_class=HTMLResponse)
        self._router.add_api_route("/search", self.search_results, methods=["GET"], response_class=HTMLResponse)
        self._router.add_api_route("/register", self.register_repo, methods=["POST"], response_class=HTMLResponse)
        self._router.add_api_route("/branches", self.list_branches, methods=["GET"], response_class=HTMLResponse)

    # ------------------------------------------------------------------
    # GET / — Search page
    # ------------------------------------------------------------------

    async def search_page(self, request: Request) -> HTMLResponse:
        """Render the main search page with repo dropdown and language filters."""
        repos = []
        try:
            session_factory = getattr(request.app.state, "session_factory", None)
            if session_factory is not None:
                async with session_factory() as session:
                    from src.shared.models.repository import Repository
                    from sqlalchemy import select
                    stmt = select(Repository).where(Repository.status == "indexed")
                    result = await session.execute(stmt)
                    repos = result.scalars().all()
        except Exception:
            log.warning("Failed to load repository list for search page", exc_info=True)

        return self._templates.TemplateResponse(
            request,
            "search.html",
            context={
                "repos": repos,
                "languages": _SUPPORTED_LANGUAGES,
            },
        )

    # ------------------------------------------------------------------
    # GET /search — Search results (htmx partial or full page)
    # ------------------------------------------------------------------

    async def search_results(
        self,
        request: Request,
        q: str = Query(default=""),
        repo: str | None = Query(default=None),
        languages: list[str] | None = Query(default=None),
    ) -> HTMLResponse:
        """Execute search and render results partial."""
        # Step 1: Validate query
        if not q or not q.strip():
            return self._render_partial(request, "partials/results.html", error="Please enter a search query")

        # Step 2: Normalize filters
        repo_filter = repo if repo and repo.strip() else None
        lang_list = languages if languages and any(l.strip() for l in languages) else None

        # Step 3: Check query handler
        query_handler = getattr(request.app.state, "query_handler", None)
        if query_handler is None:
            return self._render_partial(request, "partials/results.html", error="Search service not configured")

        # Step 4: Detect query type and dispatch
        try:
            query_type = query_handler.detect_query_type(q)
            if query_type == "symbol":
                response = await query_handler.handle_symbol_query(q, repo=repo_filter, languages=lang_list)
            else:
                response = await query_handler.handle_nl_query(q, repo=repo_filter, languages=lang_list)
        except ValidationError as e:
            return self._render_partial(request, "partials/results.html", error=str(e))
        except RetrievalError:
            return self._render_partial(request, "partials/results.html", error="Search service unavailable. Please try again.")
        except Exception:
            log.exception("Unexpected error during search")
            return self._render_partial(request, "partials/results.html", error="An unexpected error occurred.")

        # Step 5: Check for empty results
        if not response.code_results and not response.doc_results:
            return self._render_partial(request, "partials/results.html", empty=True, query=q)

        # Step 6: Highlight code results
        highlighted_results = []
        for result in response.code_results:
            highlighted_html = self._highlighter.highlight(result.content, result.language)
            highlighted_results.append({"result": result, "highlighted": highlighted_html})

        return self._render_partial(
            request,
            "partials/results.html",
            code_results=highlighted_results,
            doc_results=response.doc_results,
            query=q,
            degraded=response.degraded,
        )

    # ------------------------------------------------------------------
    # POST /register — Register a repository
    # ------------------------------------------------------------------

    async def register_repo(
        self,
        request: Request,
        url: str = Form(default=""),
        branch: str = Form(default=""),
    ) -> HTMLResponse:
        """Register a new repository."""
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is None:
            return self._render_partial(request, "partials/register_result.html", error="Database not configured")

        branch_val = branch if branch and branch.strip() else None
        try:
            async with session_factory() as session:
                mgr = RepoManager(session)
                repo = await mgr.register(url, branch=branch_val)
                await session.commit()
            return self._render_partial(
                request,
                "partials/register_result.html",
                success=True,
                repo_name=repo.name,
            )
        except ValidationError as e:
            return self._render_partial(request, "partials/register_result.html", error=str(e))
        except ConflictError as e:
            return self._render_partial(request, "partials/register_result.html", error=str(e))
        except Exception:
            log.exception("Unexpected error during registration")
            return self._render_partial(request, "partials/register_result.html", error="Registration failed unexpectedly.")

    # ------------------------------------------------------------------
    # GET /branches — List remote branches (htmx partial)
    # ------------------------------------------------------------------

    async def list_branches(
        self,
        request: Request,
        repo_id: str = Query(default=""),
    ) -> HTMLResponse:
        """Fetch remote branches and render branch options partial."""
        branches: list[str] = []
        default_branch = "main"
        try:
            git_cloner = getattr(request.app.state, "git_cloner", None)
            if git_cloner is not None and repo_id:
                result = await git_cloner.list_remote_branches_by_url(repo_id)
                if result:
                    branches = result
                    if "main" in branches:
                        default_branch = "main"
                    elif branches:
                        default_branch = branches[0]
        except Exception:
            log.warning("Failed to list branches", exc_info=True)

        return self._render_partial(
            request,
            "partials/branches.html",
            branches=branches,
            default_branch=default_branch,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render_partial(self, request: Request, template: str, **context) -> HTMLResponse:
        return self._templates.TemplateResponse(request, template, context=context)
