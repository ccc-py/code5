"""API routes for code5 web interface."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import app as web_app

router = APIRouter(prefix="/api")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def get_use_mock() -> bool:
    """Check if MOCK mode should be used."""
    env = os.environ.get("CODE5_WEB_USE_MOCK", "true")
    return env.lower() == "true"


def create_client_and_agent():
    """Create LLM client and agent based on configuration."""
    from code5.agent import Code5Agent
    from code5.client import MockClient, create_client
    from code5.config import Config, load_config_from_env
    from code5.reviewer import CommandReviewer, MockReviewer

    use_mock = get_use_mock()

    if use_mock:
        mock_client = MockClient(
            responses={"hello": "Hello! I'm Code5."},
            default_response="I'm ready. Send me a message!",
        )
        config = Config(use_mock=True)
        reviewer = MockReviewer()
    else:
        config = load_config_from_env()
        client = create_client(config)
        reviewer = CommandReviewer()

    agent = Code5Agent(
        client=mock_client if use_mock else client,
        config=config,
        reviewer=reviewer,
    )

    return agent


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response payload."""

    response: str
    session_id: str


class SessionResponse(BaseModel):
    """Session response payload."""

    session_id: str
    created_at: str
    message_count: int


@router.get("/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    """List all sessions."""
    return web_app.session_store.list()


@router.post("/sessions")
async def create_session(session_id: str | None = None) -> dict[str, Any]:
    """Create a new session."""
    session = web_app.session_store.create(session_id)
    return {"session_id": session.session_id, "created_at": session.created_at}


@router.get("/sessions/{sid}")
async def get_session(sid: str) -> dict[str, Any]:
    """Get session details and history."""
    session = web_app.session_store.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "history": session.history,
    }


@router.delete("/sessions/{sid}")
async def delete_session(sid: str) -> dict[str, str]:
    """Delete a session."""
    if web_app.session_store.delete(sid):
        return {"status": "deleted", "session_id": sid}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current server configuration."""
    return {
        "mode": "MOCK" if get_use_mock() else "LLM",
    }


def handle_message(message: str, session_history: list[dict[str, str]]) -> str:
    """Handle message - either command or LLM."""
    from .commands import execute_command, is_command

    if is_command(message):
        return execute_command(message, session_history)
    return None


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Handle chat request."""
    session_id = request.session_id
    if not session_id:
        session = web_app.session_store.create()
        session_id = session.session_id
    else:
        session = web_app.session_store.get(session_id)
        if not session:
            session = web_app.session_store.create(session_id)

    result = handle_message(request.message, session.history)
    if result:
        response = result
    else:
        agent = create_client_and_agent()
        response = await agent.run(request.message)

    session.history.append({"role": "user", "content": request.message})
    session.history.append({"role": "assistant", "content": response})

    return ChatResponse(response=response, session_id=session_id)


async def generate_chat_stream(message: str, session_id: str):
    """Generate streaming chat response."""
    from code5.client import MockClient

    yield f"data: {{\"session_id\": \"{session_id}\"}}\n\n"

    use_mock = get_use_mock()

    if use_mock:
        mock_client = MockClient(
            responses={"hello": "Hello! I'm Code5."},
            default_response="I'm ready. Send me a message!",
        )
        full_response = ""
        async for chunk in mock_client.generate_stream(message, ""):
            full_response += chunk
            yield f"data: {chunk}\n\n"
    else:
        from code5.client import create_client
        from code5.config import load_config_from_env

        config = load_config_from_env()
        client = create_client(config)
        full_response = ""
        async for chunk in client.generate_stream(message, ""):
            full_response += chunk
            yield f"data: {chunk}\n\n"

    session = web_app.session_store.get(session_id)
    if session:
        session.history.append({"role": "user", "content": message})
        session.history.append({"role": "assistant", "content": full_response})

    yield "data: [DONE]\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Handle streaming chat request."""
    from .commands import execute_command, is_command

    session_id = request.session_id
    if not session_id:
        session = web_app.session_store.create()
        session_id = session.session_id
    else:
        session = web_app.session_store.get(session_id)
        if not session:
            session = web_app.session_store.create(session_id)

    if is_command(request.message):
        result = execute_command(request.message, session.history)
        session.history.append({"role": "user", "content": request.message})
        session.history.append({"role": "assistant", "content": result})


        async def command_stream():
            yield f"data: {{\"session_id\": \"{session_id}\"}}\n\n"
            escaped = result.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
            yield f"data: {escaped}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            command_stream(),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        generate_chat_stream(request.message, session_id),
        media_type="text/event-stream",
    )


def setup_html_routes(app: FastAPI) -> None:
    """Setup HTML routes."""

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Render the main chat page."""
        return templates.TemplateResponse(request, "index.html")


def init_routes(app: FastAPI) -> None:
    """Initialize all routes."""
    app.include_router(router)
    setup_html_routes(app)
