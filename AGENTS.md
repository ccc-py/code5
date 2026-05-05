# Code5 Developer Guide

## Commands

```bash
# 互動模式 - 需要指定 session 名稱
code5 run -n mysession

# 單次執行
code5 run -n mysession "Hello"

# Mock 測試模式
code5 run -n mysession --use-mock "Hello"

# Session 管理
code5 session list           # 列出所有 session
code5 session new <name>    # 建立新 session (只是提示)
code5 session attach <name> # 檢查 session 是否存在

# 檢查設定
code5 doctor

# 對話中指令
/help     - 顯示說明
/history  - 顯示所有使用者提問
/log      - 顯示完整對話記錄
/exit     - 結束對話
```

## Mode

- **Session** - 每個 session 有獨立名稱 (-n 指定)
- **SQLite** - 資料存在 ~/.code5/code5.db
- **Mock mode** - 使用 `CODE5_USE_MOCK=true` 或 `--use-mock`

## Environment

- `NVIDIA_API_KEY` - NVIDIA NIM API key
- `CODE5_USE_MOCK=true` - use MockClient

## Testing

```bash
./test.sh          # ruff + pytest
python -m pytest tests/
```

## Architecture

```
src/code5/
├── agent.py      # Code5Agent main class
├── client.py   # LLM clients (MockClient, NVIDIAClient)
├── config.py    # Config, load_config_from_env
├── db.py        # SQLite database
├── memory.py   # ConversationMemory, KeyInfoMemory
├── prompts.py  # System prompts
├── reviewer.py # CommandReviewer (safety)
├── session.py  # Session management
└── tools.py    # ShellTool, FileTool
```