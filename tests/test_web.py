"""Tests for code5 web module."""

import pytest
from fastapi.testclient import TestClient

from code5.web.app import SessionStore, WebSession


class TestSessionStore:
    """Unit tests for SessionStore."""

    def test_create_session(self) -> None:
        """Test creating a new session."""
        store = SessionStore()
        session = store.create()
        assert session.session_id is not None
        assert len(session.history) == 0

    def test_create_with_custom_id(self) -> None:
        """Test creating session with custom ID."""
        store = SessionStore()
        session = store.create("my-session")
        assert session.session_id == "my-session"

    def test_get_session(self) -> None:
        """Test getting a session by ID."""
        store = SessionStore()
        store.create("test-id")
        retrieved = store.get("test-id")
        assert retrieved is not None
        assert retrieved.session_id == "test-id"

    def test_get_nonexistent_session(self) -> None:
        """Test getting nonexistent session returns None."""
        store = SessionStore()
        result = store.get("nonexistent")
        assert result is None

    def test_delete_session(self) -> None:
        """Test deleting a session."""
        store = SessionStore()
        store.create("to-delete")
        result = store.delete("to-delete")
        assert result is True
        assert store.get("to-delete") is None

    def test_delete_nonexistent_session(self) -> None:
        """Test deleting nonexistent session returns False."""
        store = SessionStore()
        result = store.delete("nonexistent")
        assert result is False

    def test_list_sessions(self) -> None:
        """Test listing all sessions."""
        store = SessionStore()
        store.create("session1")
        store.create("session2")
        sessions = store.list()
        assert len(sessions) == 2
        ids = [s["session_id"] for s in sessions]
        assert "session1" in ids
        assert "session2" in ids


class TestWebSession:
    """Unit tests for WebSession dataclass."""

    def test_create_empty_session(self) -> None:
        """Test creating empty session."""
        session = WebSession(session_id="test")
        assert session.session_id == "test"
        assert len(session.history) == 0
        assert session.created_at == ""

    def test_create_session_with_history(self) -> None:
        """Test creating session with initial history."""
        history = [{"role": "user", "content": "Hello"}]
        session = WebSession(session_id="test", history=history)
        assert len(session.history) == 1
        assert session.history[0]["content"] == "Hello"


class TestWebAPI:
    """API integration tests using TestClient."""

    def test_index_page(self) -> None:
        """Test that index page returns HTML."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Code5" in response.text

    def test_list_sessions_empty(self) -> None:
        """Test listing sessions when none exist."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.get("/api/sessions")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_session(self) -> None:
        """Test creating a new session."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.post("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "created_at" in data

    def test_create_session_with_custom_id(self) -> None:
        """Test creating session with custom ID."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.post("/api/sessions?session_id=my-custom-id")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "my-custom-id"

    def test_get_session(self) -> None:
        """Test getting session details."""
        from code5.web.app import app

        client = TestClient(app)
        create_resp = client.post("/api/sessions")
        session_id = create_resp.json()["session_id"]

        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["session_id"] == session_id
        assert "history" in data
        assert "created_at" in data

    def test_get_nonexistent_session(self) -> None:
        """Test getting nonexistent session returns 404."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.get("/api/sessions/nonexistent")
        assert response.status_code == 404

    def test_delete_session(self) -> None:
        """Test deleting a session."""
        from code5.web.app import app

        client = TestClient(app)
        create_resp = client.post("/api/sessions")
        session_id = create_resp.json()["session_id"]

        delete_resp = client.delete(f"/api/sessions/{session_id}")
        assert delete_resp.status_code == 200

        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_session(self) -> None:
        """Test deleting nonexistent session returns 404."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.delete("/api/sessions/nonexistent")
        assert response.status_code == 404

    def test_chat_without_session(self) -> None:
        """Test chat without providing session ID."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["session_id"] is not None

    def test_chat_with_session(self) -> None:
        """Test chat with provided session ID."""
        from code5.web.app import app

        client = TestClient(app)
        create_resp = client.post("/api/sessions")
        session_id = create_resp.json()["session_id"]

        chat_resp = client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": session_id}
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert data["session_id"] == session_id

    def test_chat_updates_history(self) -> None:
        """Test that chat updates session history."""
        from code5.web.app import app

        client = TestClient(app)
        create_resp = client.post("/api/sessions")
        session_id = create_resp.json()["session_id"]

        client.post("/api/chat", json={"message": "Hello", "session_id": session_id})
        client.post("/api/chat", json={"message": "How are you?", "session_id": session_id})

        get_resp = client.get(f"/api/sessions/{session_id}")
        data = get_resp.json()
        assert len(data["history"]) == 4  # 2 user + 2 assistant

    def test_chat_stream(self) -> None:
        """Test streaming chat endpoint using httpx."""
        import httpx

        from code5.web.app import app

        with TestClient(app) as client:
            with client.stream("POST", "/api/chat/stream", json={"message": "Hello"}) as response:
                assert response.status_code == 200
                chunks = []
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        chunks.append(line[6:])
                assert len(chunks) > 0
                assert chunks[-1] == "[DONE]"

    def test_chat_stream_with_session(self) -> None:
        """Test streaming chat with existing session using httpx."""
        from code5.web.app import app

        with TestClient(app) as client:
            create_resp = client.post("/api/sessions")
            session_id = create_resp.json()["session_id"]

            with client.stream("POST", "/api/chat/stream", json={"message": "Hello", "session_id": session_id}) as response:
                assert response.status_code == 200


class TestWebE2E:
    """End-to-end tests for web interface."""

    def test_full_conversation_flow(self) -> None:
        """Test complete conversation flow."""
        from code5.web.app import app

        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

        create_resp = client.post("/api/sessions")
        session_id = create_resp.json()["session_id"]

        chat_resp = client.post(
            "/api/chat",
            json={"message": "hello", "session_id": session_id}
        )
        assert chat_resp.status_code == 200

        history_resp = client.get(f"/api/sessions/{session_id}")
        history = history_resp.json()["history"]
        assert len(history) >= 2

        client.delete(f"/api/sessions/{session_id}")

        get_deleted = client.get(f"/api/sessions/{session_id}")
        assert get_deleted.status_code == 404

    def test_multiple_sessions_independent(self) -> None:
        """Test that multiple sessions are independent."""
        from code5.web.app import app

        client = TestClient(app)

        s1 = client.post("/api/sessions").json()["session_id"]
        s2 = client.post("/api/sessions").json()["session_id"]

        client.post("/api/chat", json={"message": "hello", "session_id": s1})
        client.post("/api/chat", json={"message": "hi there", "session_id": s2})

        h1 = client.get(f"/api/sessions/{s1}").json()["history"]
        h2 = client.get(f"/api/sessions/{s2}").json()["history"]

        assert "hello" in str(h1)
        assert "hi there" in str(h2)


class TestWebE2EBrowser:
    """Browser-style E2E tests using httpx."""

    def test_index_page_has_required_elements(self) -> None:
        """Test that index page contains required HTML elements."""
        from code5.web.app import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

        html = response.text
        assert '<header>' in html
        assert 'Code5' in html
        assert 'id="chat-container"' in html
        assert 'id="message-input"' in html
        assert 'id="send-btn"' in html

    def test_chat_streaming_returns_sse(self) -> None:
        """Test that chat/stream returns proper SSE format."""
        from code5.web.app import app

        with TestClient(app) as client:
            with client.stream("POST", "/api/chat/stream", json={"message": "test"}) as response:
                assert response.status_code == 200
                response.read()
                body = response.text
                lines = [line for line in body.split('\n') if line.startswith('data: ')]
                assert len(lines) >= 2
                assert lines[0].startswith('data: {"session_id"')
                data_parts = [line[6:] for line in lines if line.startswith('data: ') and line[6:] and line[6:] != '[DONE]']
                assert len(data_parts) >= 1

    def test_markdown_in_response(self) -> None:
        """Test that responses with markdown are stored correctly."""
        from code5.web.app import app

        client = TestClient(app)

        session_id = client.post("/api/sessions").json()["session_id"]

        client.post("/api/chat", json={
            "message": "show me markdown",
            "session_id": session_id
        })

        history = client.get(f"/api/sessions/{session_id}").json()["history"]
        assert len(history) >= 2

    def test_session_persistence(self) -> None:
        """Test that sessions persist messages correctly."""
        from code5.web.app import app

        client = TestClient(app)

        session_id = client.post("/api/sessions?session_id=test-persist").json()["session_id"]
        assert session_id == "test-persist"

        client.post("/api/chat", json={"message": "first", "session_id": session_id})
        client.post("/api/chat", json={"message": "second", "session_id": session_id})

        history = client.get(f"/api/sessions/{session_id}").json()["history"]
        assert len(history) == 4

    def test_config_endpoint(self) -> None:
        """Test that config endpoint returns correct mode."""
        import os

        from code5.web.app import app

        os.environ["CODE5_WEB_USE_MOCK"] = "true"
        with TestClient(app) as client:
            resp = client.get("/api/config")
            assert resp.json()["mode"] == "MOCK"

        os.environ["CODE5_WEB_USE_MOCK"] = "false"
        with TestClient(app) as client:
            resp = client.get("/api/config")
            assert resp.json()["mode"] == "LLM"

    def test_concurrent_sessions(self) -> None:
        """Test that concurrent sessions don't interfere."""
        import os
        os.environ["CODE5_WEB_USE_MOCK"] = "true"

        from code5.web.app import app

        with TestClient(app) as client:
            s1 = client.post("/api/sessions", json={"session_id": "session-a"}).json()["session_id"]
            s2 = client.post("/api/sessions", json={"session_id": "session-b"}).json()["session_id"]

            client.post("/api/chat", json={"message": "msg for A", "session_id": s1})
            client.post("/api/chat", json={"message": "msg for B", "session_id": s2})
            client.post("/api/chat", json={"message": "msg2 for A", "session_id": s1})

            h1 = client.get(f"/api/sessions/{s1}").json()["history"]
            h2 = client.get(f"/api/sessions/{s2}").json()["history"]

            assert "msg for A" in str(h1)
            assert "msg2 for A" in str(h1)
            assert "msg for B" in str(h2)
            assert "msg2 for A" not in str(h2)


class TestWebPlaywright:
    """Playwright browser E2E tests."""

    @pytest.fixture(autouse=True)
    def setup_playwright(self):
        """Setup Playwright and start server."""
        import os
        import subprocess
        import time
        import urllib.request

        os.environ["CODE5_WEB_USE_MOCK"] = "true"

        self.server_process = subprocess.Popen(
            ["python3", "-m", "code5.web", "--mock", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        for _ in range(10):
            try:
                urllib.request.urlopen("http://localhost:8000/", timeout=1)
                break
            except Exception:
                time.sleep(0.5)

        from playwright.sync_api import sync_playwright

        headless = os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        yield
        self.context.close()
        self.browser.close()
        self.playwright.stop()
        self.server_process.terminate()
        self.server_process.wait()
        time.sleep(1)

    def test_homepage_loads(self) -> None:
        """Test that homepage loads with Code5 title."""
        self.page.goto("http://localhost:8000")
        self.page.wait_for_load_state("networkidle")
        title = self.page.title()
        assert "Code5" in title
        header = self.page.locator("header h1").text_content()
        assert "Code5" in header

    def test_send_message_and_see_response(self) -> None:
        """Test sending a message and getting response."""
        self.page.goto("http://localhost:8000")
        self.page.wait_for_load_state("networkidle")
        self.page.fill("#message-input", "hello")
        self.page.click("#send-btn")
        self.page.wait_for_timeout(2000)
        messages = self.page.locator(".message").all()
        assert len(messages) >= 2

    def test_markdown_rendering(self) -> None:
        """Test that markdown is rendered in response."""
        self.page.goto("http://localhost:8000")
        self.page.wait_for_load_state("networkidle")
        self.page.fill("#message-input", "hello")
        self.page.click("#send-btn")
        self.page.wait_for_selector(".message.assistant", timeout=5000)
        self.page.wait_for_timeout(1000)
        response_div = self.page.locator(".message.assistant").last
        html = response_div.inner_html()
        assert len(html) > 0, "Response should have content"

    def test_sessions_panel(self) -> None:
        """Test sessions panel functionality."""
        self.page.goto("http://localhost:8000")
        self.page.wait_for_load_state("networkidle")
        self.page.click("#sessions-btn")
        self.page.wait_for_selector("#sessions-panel.open")
        self.page.click("#new-session-btn")
        self.page.wait_for_timeout(500)
        sessions = self.page.locator(".session-item").all()
        assert len(sessions) >= 1


class TestWebCommands:
    """Unit tests for web commands module."""

    def test_is_command(self) -> None:
        """Test command detection."""
        from code5.web.commands import is_command

        assert is_command("/shell ls") is True
        assert is_command("/history 5") is True
        assert is_command("/help") is True
        assert is_command("hello") is False
        assert is_command("  /log 10") is True

    def test_parse_command(self) -> None:
        """Test command parsing."""
        from code5.web.commands import parse_command

        cmd, args = parse_command("/shell ls -la")
        assert cmd == "/shell"
        assert args == ["ls", "-la"]

        cmd, args = parse_command("/history 5")
        assert cmd == "/history"
        assert args == ["5"]

        cmd, args = parse_command("hello")
        assert cmd == "hello"
        assert args == []

    def test_execute_shell(self) -> None:
        """Test shell command execution."""
        from code5.web.commands import execute_shell

        result = execute_shell("echo hello")
        assert "hello" in result

        result = execute_shell("pwd")
        assert result

    def test_execute_history(self) -> None:
        """Test history command."""
        from code5.web.commands import agent_store, execute_history

        agent_store.create_agent("test-agent")
        agent_store.add_conversation("test-agent", "user", "question 1")
        agent_store.add_conversation("test-agent", "assistant", "answer 1")

        result = execute_history(5, "test-agent")
        assert "question 1" in result

    def test_execute_log(self) -> None:
        """Test log command."""
        from code5.web.commands import agent_store, execute_log

        agent_store.create_agent("test-agent-2")
        agent_store.add_conversation("test-agent-2", "user", "test msg")
        agent_store.add_conversation("test-agent-2", "assistant", "test response")

        result = execute_log(5, "test-agent-2")
        assert "test msg" in result

    def test_agent_management(self) -> None:
        """Test agent list/new/attach commands."""
        from code5.web.commands import (
            agent_store,
            execute_agent_attach,
            execute_agent_list,
            execute_agent_new,
        )

        result = execute_agent_list()
        assert "Agents" in result

        result = execute_agent_new("new-agent")
        assert "new-agent" in result

        result = execute_agent_attach("new-agent")
        assert "new-agent" in result

    def test_help_command(self) -> None:
        """Test help command."""
        from code5.web.commands import execute_command

        result = execute_command("/help", [])
        assert "shell" in result
        assert "history" in result
        assert "log" in result
        assert "agent" in result
