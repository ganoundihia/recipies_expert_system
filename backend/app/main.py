"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, routes
from app.api.ratelimit import DailyBudget, SlidingWindowLimiter
from app.config import Settings, get_settings
from app.db import init_db, load_kb, make_engine, make_session_factory
from app.llm.client import ChatModel
from app.service import NeSyChef

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, client: ChatModel | None = None, static_dir: Path | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_url)
        app.state.sessions = make_session_factory(engine)
        init_db(engine, app.state.sessions)
        with app.state.sessions() as session:
            app.state.chef = NeSyChef(load_kb(session), settings, client)
        yield
        engine.dispose()

    app = FastAPI(title="NeSyChef API", version="2.0.0", lifespan=lifespan, description="Hybrid baking expert system: LLM for language, rules for decisions.")
    app.state.limiter = SlidingWindowLimiter(settings.rate_limit_per_minute or 10**9)
    app.state.llm_budget = DailyBudget(settings.daily_llm_budget)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
    app.include_router(routes.router)
    app.include_router(admin.router)

    # In the Docker image the built frontend is served by the API itself (single container deploys).
    if static_dir and static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        root = static_dir.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404, "Not found")
            candidate = (root / path).resolve()
            # Serve real files inside the build folder only; every other route is handled by the React router.
            if path and candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(root / "index.html")

    return app


app = create_app(static_dir=Path(__file__).resolve().parent.parent / "static")
