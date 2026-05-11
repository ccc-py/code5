"""FastAPI application for code5 web interface."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI

WEB_DB_PATH = Path.home() / ".code5" / "web_sessions.json"


def load_sessions() -> dict:
    """Load sessions from file."""
    if WEB_DB_PATH.exists():
        try:
            with open(WEB_DB_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_sessions(sessions: dict) -> None:
    """Save sessions to file."""
    WEB_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WEB_DB_PATH, "w") as f:
        json.dump(sessions, f)


@dataclass
class WebSession:
    """Web session for chat management."""

    session_id: str
    history: list[dict[str, str]] = field(default_factory=list)
    created_at: str = ""


class SessionStore:
    """In-memory session store for web sessions with file persistence."""

    def __init__(self) -> None:
        self.sessions: dict[str, WebSession] = {}
        self.current_session_id: str | None = None
        self._load()

    def _load(self) -> None:
        """Load sessions from file."""
        data = load_sessions()
        for sid, info in data.items():
            session = WebSession(
                session_id=sid,
                history=info.get("history", []),
                created_at=info.get("created_at", ""),
            )
            self.sessions[sid] = session

    def _save(self) -> None:
        """Save sessions to file."""
        data = {}
        for sid, session in self.sessions.items():
            data[sid] = {
                "history": session.history,
                "created_at": session.created_at,
            }
        save_sessions(data)

    def create(self, session_id: str | None = None) -> WebSession:
        sid = session_id or str(uuid.uuid4())[:8]
        session = WebSession(session_id=sid)
        self.sessions[sid] = session
        self.current_session_id = sid
        self._save()
        return session

    def set_current(self, session_id: str) -> bool:
        """Set current session."""
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False

    def get(self, session_id: str) -> WebSession | None:
        return self.sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Clear all sessions from memory and disk."""
        self.sessions.clear()
        self.current_session_id = None
        if WEB_DB_PATH.exists():
            WEB_DB_PATH.unlink()

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
