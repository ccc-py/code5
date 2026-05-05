"""測試代理模組"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from code5.agent import Code5Agent, EndPattern, ReadPattern, ShellPattern, WritePattern
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


class TestReadPattern:
    """讀取標籤正則表達式測試"""

    def test_match_read(self) -> None:
        """測試匹配 read 標籤"""
        text = "<read>/path/to/file.txt</read>"
        matches = ReadPattern.findall(text)
        assert len(matches) == 1
        assert "/path/to/file.txt" in matches[0]


class TestWritePattern:
    """寫入標籤正則表達式測試"""

    def test_match_write(self) -> None:
        """測試匹配 write 標籤"""
        text = "<write>/path/to/file.txt\ncontent here</write>"
        matches = WritePattern.findall(text)
        assert len(matches) == 1


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
