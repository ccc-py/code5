
執行方式
1. 安裝
cd /Users/Shared/ccc/project/code5
pip install -e ".[dev]"
2. Mock 模式（不需要 API key）
code5 --use-mock "說 hello"
3. NVIDIA 模式（需要 API key）
export NVIDIA_API_KEY="nvapi-xxx"
code5 "幫我寫一個 hello.py"
4. 互動模式
code5
# 然後輸入指令
# 你：說 hello
# 代理：...
# 特殊指令：
# /quit - 結束
# /memory - 顯示記憶的關鍵資訊
# /session - 列出 sessions
5. Python 程式使用
from code5 import Code5Agent, MockClient
agent = Code5Agent(client=MockClient())
result = await agent.run("說 hello")
print(result)
6. 執行測試
./test.sh
# 或
python -m pytest tests/ -v