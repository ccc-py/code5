# Code5 Developer Guide

This file provides guidelines for agentic coding agents working in this repository.

## CLI Commands

```bash
code5 /new <name>           # new session, interactive
code5 /attach <name>        # resume session, interactive
code5 /list                # list all sessions
code5 /doctor              # diagnose config
code5 /version             # show version
```

## Interactive Commands

`/help` | `/history <n>` | `/log <n>` | `/shell <cmd>` | `/list, /new, /attach` | `/agent` | `/bg <prompt>` | `/jobs` | `/exit`

## Environment

`NVIDIA_API_KEY`, `NVIDIA_MODEL` (default: minimaxai/minimax-m2.7), `NVIDIA_BASE_URL`, `CODE5_USE_MOCK=true`

## Testing Commands

```bash
# Full test pipeline (installs dev deps, lints, runs tests)
./test.sh

# Run all tests
pytest tests/ -v

# Run single test file
pytest tests/test_agent.py -v

# Run single test function
pytest tests/test_agent.py::test_agent_run_simple -v

# Run with verbose output
pytest tests/ -v --tb=short

# Run tests matching a pattern
pytest tests/ -k "test_agent"
```

## Linting

```bash
# Run ruff linter
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

**Order**: ruff check (warnings allowed) → pytest

## Code Style Guidelines

### Formatting

- **Line length**: 100 characters (configured in pyproject.toml)
- **Target Python**: 3.10+
- **Linter**: ruff with rules E, F, W, I, N, UP, B, C4

### Imports

- Use relative imports within the package: `from .client import ...`
- Use `TYPE_CHECKING` for type imports that shouldn't be runtime dependencies
- Group imports: stdlib, third-party, local (alphabetical within groups)

### Type Hints

- Use Python 3.10+ union syntax: `LLMClient | None` instead of `Optional[LLMClient]`
- Use type hints for all function parameters and return values
- Use `TYPE_CHECKING` block for circular imports

### Naming Conventions

- **Classes**: `CamelCase` (e.g., `Code5Agent`, `NVIDIAClient`)
- **Functions/variables**: `snake_case` (e.g., `create_client`, `shell_timeout`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONFIG`)
- **Private methods**: prefix with underscore (e.g., `_extract_key_info`)

### Dataclasses

Use `@dataclass` for simple data containers:

### Error Handling

- Use specific exception types (e.g., `ValueError`, `RuntimeError`)
- Chain exceptions with `from e` to preserve tracebacks
- Handle async errors with try/except in async functions

### Docstrings

- Use docstrings for public classes and functions
- Include Args and Returns sections for complex functions
- Can be in Chinese or English (existing codebase uses both)

### Async Code

- Use `async def` for asynchronous functions
- Use `pytest-asyncio` with `@pytest.mark.asyncio` decorator
- Use `async with` for context managers

### Testing Patterns

- Use `MockClient` for testing without API calls
- Use `pytest-mock` for mocking
- Test files: `tests/test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

```python
from code5.client import MockClient
from code5.config import Config
from code5.reviewer import MockReviewer

mock_client = MockClient(responses={"hello": "Hello!"})
config = Config(use_mock=True)
agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
```

## Development Rules (陳鍾誠規範)

- 必須寫單元測試和系統測試
- 必須有 `test.sh` 做專案測試
- 程式超過 1000 行需強制分模組
- 每個版本規劃寫在 `_doc/vx.y.md`（如 v0.1.md, v0.2.md），每次進版前進 0.1 版
- 語法必須修改到沒有 warning

## Architecture

Package in `src/code5/`, CLI entry via `code5` or `python -m code5`.

| File | Description |
|------|-------------|
| `__main__.py` | CLI entry point (click-based) |
| `agent.py` | Code5Agent (main agent logic) |
| `client.py` | MockClient, NVIDIAClient, create_client |
| `config.py` | Config, load_config_from_env |
| `db.py` | SQLite database (~/.code5/code5.db) |
| `memory.py` | ConversationMemory, KeyInfoMemory |
| `prompts.py` | System prompts |
| `reviewer.py` | CommandReviewer (security) |
| `session.py` | Session manager |
| `tools.py` | ShellTool, FileTool |
| `web_server.py` | Web server entry (uvicorn) |
| `web/` | FastAPI web module |
| `web/app.py` | FastAPI app, SessionStore |
| `web/routes.py` | API routes |
| `web/templates/` | HTML templates |