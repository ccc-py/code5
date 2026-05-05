# Code5 - NVIDIA AI Coding Agent

一個類似 OpenCode 的開源 AI Coding Agent，使用 NVIDIA NIM 服務作為 LLM 後端。

## 功能特色

- **AI 對話式編碼輔助** - 使用自然語言與 AI 互動
- **Shell 命令執行** - 自動執行 shell 命令
- **安全審查** - 防止執行危險命令
- **對話記憶** - 滾動歷史 + 關鍵資訊提取
- **多 Session 支援** - 支援多個獨立對話
- **Mock 模式** - 測試無需呼叫真實 LLM

## 安裝

```bash
pip install code5
```

或開發模式：

```bash
pip install -e ".[dev]"
```

## 快速開始

### 使用 Mock 模式（測試用）

```python
from code5 import Code5Agent, MockClient

agent = Code5Agent(client=MockClient())
result = await agent.run("Hello!")
```

### 使用 NVIDIA NIM

```python
from code5 import Code5Agent, Config
from code5.client import NVIDIAClient

config = Config(api_key="nvapi-xxx")
agent = Code5Agent(client=NVIDIAClient(config))
result = await agent.run("Help me write a function")
```

### CLI 使用

```bash
# 互動模式
code5

# 單次執行
code5 "幫我寫一個 hello.py"

# 使用 mock
code5 --use-mock "Hello"
```

## 設定

透過環境變數：

- `NVIDIA_API_KEY` - NVIDIA NIM API key
- `NVIDIA_MODEL` - 模型名稱（預設：minimaxai/minimax-m2.7）
- `NVIDIA_BASE_URL` - API 端點
- `CODE5_USE_MOCK` - 設為 `true` 使用 mock 模式

## 測試

```bash
./test.sh
```

## 專案結構

```
code5/
├── src/code5/
│   ├── __init__.py      # 套件導出
│   ├── agent.py         # 主要 Agent 類別
│   ├── client.py        # LLM 客戶端
│   ├── config.py        # 設定管理
│   ├── memory.py        # 記憶體管理
│   ├── prompts.py       # System prompts
│   ├── reviewer.py      # 安全審查
│   ├── session.py       # Session 管理
│   ├── tools.py         # 工具執行
│   └── __main__.py      # CLI 入口
└── tests/              # 測試檔案
```

## 授權

MIT License