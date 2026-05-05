"""Code5 - NVIDIA AI Coding Agent.

A Python package that provides an OpenCode-like AI coding agent using NVIDIA NIM services.

Example:
    from code5 import Code5Agent, Config, MockClient

    # Using mock for testing
    agent = Code5Agent(client=MockClient())
    result = await agent.run("Hello")

    # Using real NVIDIA API
    config = Config(api_key="nvapi-xxx")
    from code5.client import NVIDIAClient
    agent = Code5Agent(client=NVIDIAClient(config))
    result = await agent.run("Help me write a function")
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your@email.com"

from .agent import Code5Agent
from .client import LLMClient, MockClient, NVIDIAClient, create_client
from .config import DEFAULT_CONFIG, Config, SessionConfig, load_config_from_env
from .memory import (
    ConversationMemory,
    KeyInfoMemory,
    MemoryManager,
    extract_key_info_from_text,
)
from .reviewer import CommandReviewer, MockReviewer, ReviewResult
from .session import Session, SessionManager
from .tools import CommandResult, FileTool, ShellTool, ToolExecutor, check_outside_access

__all__ = [
    "Code5Agent",
    "LLMClient",
    "NVIDIAClient",
    "MockClient",
    "create_client",
    "Config",
    "SessionConfig",
    "load_config_from_env",
    "DEFAULT_CONFIG",
    "ConversationMemory",
    "KeyInfoMemory",
    "MemoryManager",
    "extract_key_info_from_text",
    "CommandReviewer",
    "MockReviewer",
    "ReviewResult",
    "Session",
    "SessionManager",
    "ShellTool",
    "FileTool",
    "ToolExecutor",
    "CommandResult",
    "check_outside_access",
]
