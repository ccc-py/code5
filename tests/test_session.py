"""Tests for session module."""

import json
from pathlib import Path

import pytest

from code5.session import Session, SessionManager


class TestSession:
    def test_create_session(self) -> None:
        session = Session(session_id="test-123")
        assert session.session_id == "test-123"
        assert session.created_at is not None

    def test_to_dict(self) -> None:
        session = Session(session_id="test-123")
        data = session.to_dict()
        assert data["session_id"] == "test-123"
        assert "created_at" in data
        assert "updated_at" in data
        assert "memory" in data

    def test_from_dict(self) -> None:
        data = {
            "session_id": "test-456",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "memory": {"conversation": [], "key_info": [], "outside_access_granted": []},
            "metadata": {},
        }
        session = Session.from_dict(data)
        assert session.session_id == "test-456"

    def test_roundtrip(self) -> None:
        session = Session(session_id="roundtrip-test")
        session.memory.update(user_input="Hello", assistant_response="Hi!")
        session.memory.key_info.add("Important info")

        data = session.to_dict()
        restored = Session.from_dict(data)

        assert restored.session_id == session.session_id
        assert len(restored.memory.conversation) == 2


class TestSessionManager:
    def test_create_session_manager(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        assert manager.storage_path == tmp_path

    def test_create_new_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        session = manager.create_session()
        assert session.session_id is not None
        assert len(session.session_id) == 8
        assert manager.get_session(session.session_id) is not None

    def test_create_named_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        session = manager.create_session(session_id="my-session")
        assert session.session_id == "my-session"

    def test_get_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        created = manager.create_session()
        retrieved = manager.get_session(created.session_id)
        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    def test_get_nonexistent_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        result = manager.get_session("nonexistent")
        assert result is None

    def test_delete_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        session = manager.create_session()
        result = manager.delete_session(session.session_id)
        assert result is True
        assert manager.get_session(session.session_id) is None

    def test_delete_nonexistent_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        result = manager.delete_session("nonexistent")
        assert result is False

    def test_list_sessions(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        manager.create_session(session_id="session-1")
        manager.create_session(session_id="session-2")
        sessions = manager.list_sessions()
        assert len(sessions) == 2

    def test_current_session_after_create(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        manager.create_session(session_id="first")
        manager.create_session(session_id="second")
        current = manager.current_session()
        assert current is not None
        assert current.session_id == "second"

    def test_set_current_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        manager.create_session(session_id="session-1")
        manager.create_session(session_id="session-2")
        manager.set_current_session("session-1")
        current = manager.current_session()
        assert current is not None
        assert current.session_id == "session-1"

    def test_set_current_session_invalid(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        manager.create_session()
        result = manager.set_current_session("nonexistent")
        assert result is False

    def test_save_and_load_persistence(self, tmp_path: Path) -> None:
        manager1 = SessionManager(storage_path=tmp_path)
        session = manager1.create_session(session_id="persist-test")
        session.memory.update(user_input="Hello")
        manager1.save_current_session()

        manager2 = SessionManager(storage_path=tmp_path)
        loaded = manager2.get_session("persist-test")
        assert loaded is not None
        assert len(loaded.memory.conversation) == 1

    def test_export_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        session = manager.create_session(session_id="export-test")
        session.memory.update(user_input="Hello")
        exported = manager.export_session("export-test")
        assert exported is not None
        data = json.loads(exported)
        assert data["session_id"] == "export-test"

    def test_export_nonexistent_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        result = manager.export_session("nonexistent")
        assert result is None

    def test_import_session(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        session = manager.create_session(session_id="import-test")
        session.memory.update(user_input="Hello")
        exported = manager.export_session("import-test")

        manager2 = SessionManager(storage_path=tmp_path)
        imported = manager2.import_session(exported)
        assert imported is not None
        assert imported.session_id == "import-test"

    def test_import_invalid_json(self, tmp_path: Path) -> None:
        manager = SessionManager(storage_path=tmp_path)
        result = manager.import_session("not valid json")
        assert result is None
