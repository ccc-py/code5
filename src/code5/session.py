"""Session management for code5 - multi-session support with persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .memory import MemoryManager


@dataclass
class Session:
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    memory: MemoryManager = field(default_factory=MemoryManager)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "memory": self.memory.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        session = cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )
        session.memory = MemoryManager.from_dict(data.get("memory", {}))
        return session


class SessionManager:
    """Manage multiple sessions with persistence."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("~/.code5/sessions")
        self.storage_path = Path(self.storage_path).expanduser()
        self.sessions: dict[str, Session] = {}
        self._current_session_id: str | None = None
        self._load_sessions()

    def _load_sessions(self) -> None:
        if not self.storage_path.exists():
            self.storage_path.mkdir(parents=True, exist_ok=True)
            return

        for session_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                session = Session.from_dict(data)
                self.sessions[session.session_id] = session
            except Exception:
                continue

    def _save_session(self, session: Session) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        session.updated_at = datetime.now()
        file_path = self.storage_path / f"{session.session_id}.json"
        file_path.write_text(json.dumps(session.to_dict(), indent=2))

    def create_session(self, session_id: str | None = None, metadata: dict | None = None) -> Session:
        if session_id is None:
            session_id = str(uuid.uuid4())[:8]

        session = Session(
            session_id=session_id,
            metadata=metadata or {},
        )
        self.sessions[session_id] = session
        self._save_session(session)
        self._current_session_id = session_id
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False

        del self.sessions[session_id]
        file_path = self.storage_path / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()

        if self._current_session_id == session_id:
            self._current_session_id = None

        return True

    def list_sessions(self) -> list[Session]:
        return sorted(self.sessions.values(), key=lambda s: s.updated_at, reverse=True)

    def current_session(self) -> Session | None:
        if self._current_session_id:
            return self.sessions.get(self._current_session_id)
        if self.sessions:
            latest = sorted(self.sessions.values(), key=lambda s: s.updated_at, reverse=True)
            return latest[0] if latest else None
        return self.create_session()

    def set_current_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        self._current_session_id = session_id
        return True

    def save_current_session(self) -> None:
        if self._current_session_id and self._current_session_id in self.sessions:
            self._save_session(self.sessions[self._current_session_id])

    def export_session(self, session_id: str) -> str | None:
        session = self.get_session(session_id)
        if not session:
            return None
        return json.dumps(session.to_dict(), indent=2)

    def import_session(self, json_str: str) -> Session | None:
        try:
            data = json.loads(json_str)
            session = Session.from_dict(data)
            self.sessions[session.session_id] = session
            self._save_session(session)
            return session
        except Exception:
            return None
