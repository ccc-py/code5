"""Web module for code5 - FastAPI web interface."""

from ..web_server import main
from .app import app

__all__ = ["app", "main"]
