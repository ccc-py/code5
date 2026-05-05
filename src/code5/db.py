"""SQLite database for code5 conversation history and key info."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Self


class Database:
    """SQLite database for storing conversation history."""

    _instance: Self | None = None

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path("~/.code5/code5.db")
        self.db_path = Path(self.db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Path | None = None) -> Database:
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # key_info table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session
            ON conversations(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_key_info_session
            ON key_info(session_id)
        """)

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection."""
        return sqlite3.connect(self.db_path)

    def add_conversation(self, session_id: str, role: str, content: str) -> None:
        """Add a conversation turn."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_conversations(self, session_id: str) -> list[dict]:
        """Get all conversations for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, created_at FROM conversations WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {"role": r[0], "content": r[1], "created_at": r[2]}
            for r in rows
        ]

    def get_user_conversations(self, session_id: str) -> list[str]:
        """Get only user questions for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM conversations WHERE session_id = ? AND role = 'user' ORDER BY id",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def add_key_info(self, session_id: str, content: str) -> None:
        """Add key info."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO key_info (session_id, content, created_at) VALUES (?, ?, ?)",
            (session_id, content, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_key_info(self, session_id: str) -> list[str]:
        """Get all key info for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM key_info WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def clear_session(self, session_id: str) -> None:
        """Clear all data for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM key_info WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()