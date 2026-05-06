# Code5 Developer Guide

## CLI Commands

```bash
code5 /new <name>           # 新 session，進入互動
code5 /attach <name>       # 繼續 session，進入互動
code5 /list                # 列出所有 session
code5 /doctor              # 檢查設定
code5 /version             # 顯示版本

# 批次執行
code5 /new mysession <<EOF
Hello
/exit
EOF
```

## Interactive Commands

在互動模式中使用:
- `/help` - 顯示說明
- `/history` - 顯示提問歷史
- `/log` - 顯示完整對話記錄
- `/shell <cmd>` - 執行 shell 命令
- `/session list/new/attach` - Session 管理 (deprecated，改用 /list, /new, /attach)
- `/agent list/new/attach/history/log` - Agent 管理
- `/bg <prompt>` - 背景執行，不等待結果
- `/jobs` - 查看背景任務狀態
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
├── __init__.py     # 套件導出
├── __main__.py     # CLI 入口
├── agent.py       # Code5Agent
├── client.py      # MockClient, NVIDIAClient, create_client
├── config.py      # Config, load_config_from_env
├── db.py          # SQLite 資料庫 (~/.code5/code5.db)
├── memory.py      # ConversationMemory, KeyInfoMemory
├── prompts.py     # System prompts
├── reviewer.py     # CommandReviewer
├── session.py     # Session manager
├── simple_cli.py  # 簡化 CLI
└── tools.py      # ShellTool, FileTool
```