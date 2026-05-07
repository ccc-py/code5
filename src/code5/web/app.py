"""FastAPI application for code5 web interface."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI


@dataclass
class WebSession:
    """Web session for chat management."""

    session_id: str
    history: list[dict[str, str]] = field(default_factory=list)
    created_at: str = ""


class SessionStore:
    """In-memory session store for web sessions."""

    def __init__(self) -> None:
        self.sessions: dict[str, WebSession] = {}

    def create(self, session_id: str | None = None) -> WebSession:
        sid = session_id or str(uuid.uuid4())[:8]
        session = WebSession(session_id=sid)
        self.sessions[sid] = session
        return session

    def get(self, session_id: str) -> WebSession | None:
        return self.sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def list(self) -> list[dict[str, Any]]:
        return [
            {"session_id": s.session_id, "created_at": s.created_at, "message_count": len(s.history)}
            for s in self.sessions.values()
        ]


session_store = SessionStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    from . import routes

    app = FastAPI(
        title="Code5",
        description="AI Coding Agent Web Interface",
        version="0.8.0",
        lifespan=lifespan,
    )

    routes.init_routes(app)

    return app


app = create_app()
