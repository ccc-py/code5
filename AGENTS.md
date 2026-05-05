# Code5 Developer Guide

## CLI Commands

```bash
code5 run -n mysession              # 互動模式 (session 名稱 required)
code5 run -n mysession "Hello"      # 單次執行
code5 run -n mysession --use-mock "Hello"  # Mock 測試
code5 session list                 # 列出所有 session
code5 doctor                      # 檢查設定
```

## Interactive Commands

在互動模式中使用:
- `/help` - 顯示說明
- `/history` - 顯示提問歷史
- `/log` - 顯示完整對話記錄
- `/shell <cmd>` - 執行 shell 命令
- `/session list/new/attach` - Session 管理
- `/agent list/new/attach/history` - Agent 管理
- `/exit` - 結束對話

## Environment

- `NVIDIA_API_KEY` - NVIDIA NIM API key
- `CODE5_USE_MOCK=true` - 使用 MockClient
- `NVIDIA_MODEL` - 模型名稱 (預設: minimaxai/minimax-m2.7)

## Testing

```bash
./test.sh                    # ruff + pytest
pytest tests/ -v            # 全部測試
pytest tests/test_xxx.py::test_func -v  # 單一測試
```

Order: ruff check (warnings allowed) → pytest

## Architecture

```
src/code5/
├── agent.py      # Code5Agent
├── client.py    # MockClient, NVIDIAClient
├── config.py    # Config, load_config_from_env
├── db.py        # SQLite (~/.code5/code5.db)
├── memory.py    # ConversationMemory, KeyInfoMemory
├── prompts.py   # System prompts
├── reviewer.py  # CommandReviewer
├── session.py   # Session manager
└── tools.py     # ShellTool, FileTool
```