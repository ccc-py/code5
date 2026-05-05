"""Pytest configuration and fixtures for code5 tests."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def close_aiohttp_sessions():
    """Close any open aiohttp sessions after each test."""
    yield
    # Cleanup any lingering sessions
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            # Let pending tasks complete briefly
            pass
    except RuntimeError:
        pass
