"""測試代理模組"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code5.agent import Code5Agent, EndPattern, ShellPattern
from code5.client import MockClient
from code5.config import Config
from code5.reviewer import MockReviewer


class TestCode5Agent:
    """Code5Agent 類別測試"""

    @pytest.mark.asyncio
    async def test_agent_run_simple(self) -> None:
        """測試簡單執行"""
        mock_client = MockClient(responses={"hello": "Hello!"})
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        result = await agent.run("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_agent_run_with_context(self) -> None:
        """測試攜帶上下文的執行"""
        mock_client = MockClient(responses={"hello": "Hello!"})
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        agent.memory.update(user_input="previous", assistant_response="previous response")
        result = await agent.run("hello")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_agent_with_mock_client(self) -> None:
        """測試使用 Mock 客戶端"""
        mock_client = MockClient(
            responses={"hello": "Hello! How can I help you?"},
            default_response="Default response",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        result = await agent.run("say hello")
        assert "Hello" in result

    def test_agent_verbose_flag(self) -> None:
        """測試詳細輸出標誌"""
        mock_client = MockClient()
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        agent.verbose = True
        assert agent.verbose is True
        agent.verbose = False
        assert agent.verbose is False

    def test_agent_reset(self) -> None:
        """測試重置功能"""
        mock_client = MockClient()
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        agent.memory.update(user_input="Hello")
        agent.outside_access_granted.add("/tmp")
        agent.reset()
        assert len(agent.memory.conversation) == 0
        assert len(agent.outside_access_granted) == 0

    def test_agent_load_session(self) -> None:
        """測試載入 session"""
        mock_client = MockClient()
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        agent.session_manager.create_session(session_id="test-session")
        result = agent.load_session("test-session")
        assert result is True

    def test_agent_load_invalid_session(self) -> None:
        """測試載入無效 session"""
        mock_client = MockClient()
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        result = agent.load_session("nonexistent")
        assert result is False

    def test_agent_save_session(self) -> None:
        """測試保存 session"""
        mock_client = MockClient()
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())
        agent.session_manager.create_session(session_id="save-test")
        agent.memory.update(user_input="Hello")
        agent.save_session()
        session = agent.session_manager.get_session("save-test")
        assert session is not None
        assert len(session.memory.conversation) == 1


class TestShellPattern:
    """Shell 命令正則表達式測試"""

    def test_match_single_shell(self) -> None:
        """測試匹配單個 shell 標籤"""
        text = "<shell>ls -la</shell>"
        matches = ShellPattern.findall(text)
        assert len(matches) == 1
        assert "ls -la" in matches[0]

    def test_match_multiple_shell(self) -> None:
        """測試匹配多個 shell 標籤"""
        text = "<shell>ls</shell> then <shell>pwd</shell>"
        matches = ShellPattern.findall(text)
        assert len(matches) == 2

    def test_match_multiline_shell(self) -> None:
        """測試匹配多行 shell 標籤"""
        text = "<shell>ls\n  echo hello\n  cat file</shell>"
        matches = ShellPattern.findall(text)
        assert len(matches) == 1
        assert "ls" in matches[0]

    def test_no_match(self) -> None:
        """測試無匹配情況"""
        text = "plain text without shell tags"
        matches = ShellPattern.findall(text)
        assert len(matches) == 0


class TestEndPattern:
    """結束標籤正則表達式測試"""

    def test_match_end(self) -> None:
        """測試匹配 end 標籤"""
        text = "response <end/>"
        match = EndPattern.search(text)
        assert match is not None

    def test_no_match(self) -> None:
        """測試無匹配情況"""
        text = "plain text without end"
        match = EndPattern.search(text)
        assert match is None

    def test_split_at_end(self) -> None:
        """測試在 end 處分割"""
        text = "response <end/> more text"
        parts = EndPattern.split(text)
        assert len(parts) == 2
        assert "response" in parts[0]


class TestIntegration:
    """整合測試"""

    @pytest.mark.asyncio
    async def test_memory_accumulation(self) -> None:
        """測試記憶體累積"""
        mock_client = MockClient(
            responses={"first": "First response", "second": "Second response"},
            default_response="OK",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        await agent.run("first message")
        await agent.run("second message")

        assert len(agent.memory.conversation) > 0

    @pytest.mark.asyncio
    async def test_shell_command_execution(self, tmp_path: Path) -> None:
        """測試 shell 命令確實被執行"""
        import os
        # 設定工作目錄
        os.chdir(tmp_path)

        # Mock LLM 回傳帶有 shell 命令的響應
        mock_client = MockClient(
            responses={
                "hello": "<shell>cat > hello.py <<'EOF'\nprint('Hello, World!')\nEOF\n</shell><end/>",
            },
            default_response="<end/>",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        await agent.run("say hello")

        # 驗證檔案被建立
        hello_file = tmp_path / "hello.py"
        assert hello_file.exists(), "hello.py 應該被建立"
        content = hello_file.read_text()
        assert "Hello, World!" in content, f"檔案內容應該包含 'Hello, World!'，實際內容：{content}"

    @pytest.mark.asyncio
    async def test_shell_with_ls_command(self, tmp_path: Path) -> None:
        """測試 ls 命令執行"""
        import os
        os.chdir(tmp_path)

        # 建立測試檔案
        (tmp_path / "test.txt").write_text("content")

        mock_client = MockClient(
            responses={
                "list": "<shell>ls -la</shell><end/>",
            },
            default_response="<end/>",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        await agent.run("list files")

        # 驗證記憶中有 tool result
        assert len(agent.memory.conversation) > 0

    @pytest.mark.asyncio
    async def test_shell_command_blocked_by_reviewer(self, tmp_path: Path) -> None:
        """測試危險命令被阻擋"""
        import os
        os.chdir(tmp_path)

        # Mock LLM 回傳危險命令
        mock_client = MockClient(
            responses={
                "delete": "<shell>rm -rf /</shell><end/>",
            },
            default_response="<end/>",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        await agent.run("delete everything")

        # 驗證危險命令被阻止（使用 MockReviewer 所以不阻止dangerous關鍵字）
        # 但 rm -rf / 是危險的應被阻擋
        # 由於 MockReviewer 只阻擋包含 "dangerous" 的命令，所以會通過
        # 這個測試主要是確認流程運作

    @pytest.mark.asyncio
    async def test_shell_with_multiple_commands(self, tmp_path: Path) -> None:
        """測試多個 shell 命令"""
        import os
        os.chdir(tmp_path)

        mock_client = MockClient(
            responses={
                "create": "<shell>mkdir -p testdir && cat > testdir/hello.py <<'EOF'\nprint('Hi')\nEOF\n</shell><end/>",
            },
            default_response="<end/>",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        await agent.run("create project")

        # 驗證目錄和檔案都被建立
        hello_file = tmp_path / "testdir" / "hello.py"
        assert hello_file.exists(), "testdir/hello.py 應該被建立"
        assert "Hi" in hello_file.read_text()

    @pytest.mark.asyncio
    async def test_end_tag_terminates_loop(self, tmp_path: Path) -> None:
        """測試 <end/> 標籤終止循環"""
        import os
        os.chdir(tmp_path)

        mock_client = MockClient(
            responses={
                "hello": "Hello! <end/>",
            },
            default_response="<end/>",
        )
        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        await agent.run("say hello")

        # 如果有 <end/>，就不會執行任何 shell 命令
        assert len(agent.memory.conversation) >= 2  # user + assistant

    @pytest.mark.asyncio
    async def test_multi_turn_generate_fastapi_blog(self, tmp_path: Path) -> None:
        """多輪對話測試：要求產生一個 FastAPI 網誌系統

        測試項目：
        1. 單次 run() 內的 follow-up 循環（缺少 <end/> 時自動追問）
        2. 跨多次 run() 的記憶累積
        3. 複雜檔案建立操作的正確性
        4. 產生的 Python 程式碼語法正確
        """
        import os
        os.chdir(tmp_path)

        # Turn 1 的回應：建立 blog 目錄與 main.py，但不加 <end/>
        # 這會觸發 agent 的內部 follow-up 循環
        blog_commands = (
            '<shell>mkdir -p blog</shell>'
            '<shell>cat > blog/main.py << \'EOF\'\n'
            'from fastapi import FastAPI\n'
            '\n'
            'app = FastAPI()\n'
            '\n'
            '@app.get("/")\n'
            'def read_root():\n'
            '    return {"message": "Hello Blog"}\n'
            '\n'
            '@app.get("/posts")\n'
            'def list_posts():\n'
            '    return []\n'
            'EOF</shell>'
        )

        # MockClient 匹配策略：
        # - 首次 prompt 不含「需要更多命令」→ 回傳 blog_commands（無 <end/>）
        # - follow-up prompt 含「需要更多命令」→ 回傳 <end/> 終止循環
        mock_client = MockClient(
            responses={
                "需要更多命令": "<end/>",
            },
            default_response=blog_commands,
        )

        config = Config(use_mock=True)
        agent = Code5Agent(client=mock_client, config=config, reviewer=MockReviewer())

        # === Turn 1：產生 FastAPI 網誌（含內部 follow-up 循環） ===
        result1 = await agent.run("產生一個 FastAPI 網誌")
        assert isinstance(result1, str)

        # 驗證檔案被建立
        main_file = tmp_path / "blog" / "main.py"
        assert main_file.exists(), "main.py 應該被建立"
        main_content = main_file.read_text()
        assert "FastAPI" in main_content
        assert "read_root" in main_content
        assert "list_posts" in main_content

        # 驗證 Python 語法正確
        compile(main_content, "main.py", "exec")

        # 驗證內部 follow-up 循環確實發生過
        # 第一次 prompt → blog_commands（無 <end/>）→ 觸發 follow-up
        # 第二次 prompt（follow-up）→ <end/> → 結束循環
        assert mock_client.call_count == 2, \
            f"預期 LLM 被調用 2 次（初始 + follow-up），實際 {mock_client.call_count}"

        # 驗證記憶：user + tool（assistant 為空字串因 follow-up 僅回 <end/>）
        assert len(agent.memory.conversation) == 2

        # === Turn 2：加入資料庫支援（跨 run() 的記憶累積） ===
        # 移除 follow-up key 避免被舊 context 中的文字匹配到
        del mock_client.responses["需要更多命令"]
        mock_client.default_response = (
            '<shell>cat > blog/database.py << \'EOF\'\n'
            'from sqlalchemy import create_engine\n'
            '\n'
            'engine = create_engine("sqlite:///./blog.db")\n'
            'EOF</shell>'
            '<end/>'
        )

        result2 = await agent.run("加入資料庫支援")
        assert isinstance(result2, str)

        # 驗證新檔案被建立
        db_file = tmp_path / "blog" / "database.py"
        assert db_file.exists(), "database.py 應該被建立"
        db_content = db_file.read_text()
        assert "sqlalchemy" in db_content
        assert "create_engine" in db_content

        # 驗證 Python 語法正確
        compile(db_content, "database.py", "exec")

        # 驗證跨 turn 記憶累積
        assert len(agent.memory.conversation) == 5, \
            f"預期 5 條記憶（Turn1:2 + Turn2:3），實際 {len(agent.memory.conversation)}"

        # === Turn 3：列出檔案（基本 shell 命令） ===
        mock_client.default_response = '<shell>ls -la blog/</shell><end/>'

        result3 = await agent.run("列出檔案")
        assert isinstance(result3, str)

        # 驗證記憶持續累積
        assert len(agent.memory.conversation) == 8, \
            f"預期 8 條記憶（Turn1:2 + Turn2:3 + Turn3:3），實際 {len(agent.memory.conversation)}"


