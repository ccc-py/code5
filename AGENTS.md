# Code5 Developer Guide

## CLI Commands

```bash
code5 /new <name>           # new session, interactive
code5 /attach <name>        # resume session, interactive
code5 /list                # list all sessions
code5 /doctor              # diagnose config
code5 /version             # show version
```

## Interactive Commands

- `/help` - show help
- `/history <n>` - show last n questions
- `/log <n>` - show last n records with key info
- `/shell <cmd>` - run shell command
- `/list, /new <name>, /attach <name>` - session management
- `/agent list/new/attach/history/log` - agent management
- `/bg <prompt>` - run in background
- `/jobs` - show background tasks
- `/exit` - end session

## Environment

- `NVIDIA_API_KEY` - NVIDIA NIM API key
- `NVIDIA_MODEL` - model name (default: minimaxai/minimax-m2.7)
- `NVIDIA_BASE_URL` - API endpoint
- `CODE5_USE_MOCK=true` - use mock mode

## Testing

```bash
./test.sh                    # ruff + pytest (dev install + lint + test)
pytest tests/ -v            # all tests
pytest tests/test_xxx.py::test_func -v  # single test
```

Order: ruff check (warnings allowed) → pytest

## Architecture

Package in `src/code5/`, CLI entry via `code5` or `python -m code5`.
- `__main__.py` - CLI entry point (click-based)
- `agent.py` - Code5Agent (main agent logic)
- `client.py` - MockClient, NVIDIAClient, create_client
- `config.py` - Config, load_config_from_env
- `db.py` - SQLite database (~/.code5/code5.db)
- `memory.py` - ConversationMemory, KeyInfoMemory
- `reviewer.py` - CommandReviewer (security)
- `session.py` - Session manager
- `tools.py` - ShellTool, FileTool