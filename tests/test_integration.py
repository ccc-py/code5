"""整合測試，包含背景執行功能"""

import asyncio
import os
import sys

import pytest

from code5 import Code5Agent, MockClient
from code5.client import NVIDIAClient, create_client
from code5.config import load_config_from_env
from code5.db import Database

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestBackgroundExecution:
    """測試背景執行功能"""

    def setup_method(self):
        self.config = load_config_from_env()
        self.config.use_mock = True
        self.client = MockClient()
        self.db = Database.get_instance()

    def teardown_method(self):
        self.db.clear_session("test_bg_history")

    @pytest.mark.asyncio
    async def test_bg_saves_to_history(self):
        """測試 /bg 指令會存入歷史"""
        self.db.clear_session("test_bg_history")

        agent = Code5Agent(
            client=self.client,
            config=self.config,
            session_id="test_bg_history",
            agent_id="root",
        )

        agent.memory.update("/bg 測試問題", "", None)
        await agent.run("一般對話")

        questions = self.db.get_user_conversations("test_bg_history", "root")
        assert "/bg 測試問題" in questions, f"Expected /bg in history, got: {questions}"
        assert "一般對話" in questions


class TestBgFix:
    """測試 /bg 修復 - 確認不影響後續指令"""

    def setup_method(self):
        self.config = load_config_from_env()
        self.config.use_mock = True
        self.client = MockClient()
        self.db = Database.get_instance()
        self.db.clear_session("test_bg_fix")

        self.agent = Code5Agent(
            client=self.client,
            config=self.config,
            session_id="test_bg_fix",
            agent_id="root",
        )

        self.current_session_id = ["test_bg_fix"]
        self.current_agent_id = ["root"]
        self.current_agent = [self.agent]
        self.pending_tasks = {}
        self.bg_outputs = {}
        self.task_counter = [0]

        from code5.__main__ import handle_command
        self.handle_command = handle_command

    def teardown_method(self):
        self.db.clear_session("test_bg_fix")

    def test_bg_then_history(self):
        """測試 /bg 後執行 /history 正常"""

        async def run():
            await self.agent.run("說 hi")

            self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            await asyncio.sleep(0.1)

            history = self.handle_command(
                "/history 10",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            assert history is not None
            assert "說 hi" in history
            assert "說 hello" in history
            assert "/bg 說 hello" in history

        asyncio.run(run())

    def test_bg_then_log(self):
        """測試 /bg 後執行 /log 正常"""

        async def run():
            await self.agent.run("說 hi")

            self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            await asyncio.sleep(0.1)

            log = self.handle_command(
                "/log 10",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            assert log is not None
            assert "完整記錄" in log
            assert "說 hi" in log

        asyncio.run(run())

    def test_bg_then_now(self):
        """測試 /bg 後執行 /now 正常"""
        import asyncio

        async def run():
            result = self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )
            assert "背景執行" in result

            now = self.handle_command(
                "/now",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )
            assert now is not None
            assert "test_bg_fix" in now

        asyncio.run(run())

    def test_bg_then_list(self):
        """測試 /bg 後執行 /list 正常"""
        import asyncio

        async def run():
            await self.agent.run("初始化")
            self.db.clear_session("test_bg_fix")
            self.db.get_conversations("test_bg_fix")

            self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            list_result = self.handle_command(
                "/list",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )
            assert list_result is not None
            assert "所有 Sessions" in list_result

        asyncio.run(run())

    def test_bg_then_help(self):
        """測試 /bg 後執行 /help 正常"""
        import asyncio

        async def run():
            self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            help_result = self.handle_command(
                "/help",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )
            assert help_result is not None
            assert "可用指令" in help_result

        asyncio.run(run())

    def test_bg_stdout_restored(self):
        """測試 /bg 後 stdout 已恢復, 不影響全域輸出"""
        import asyncio
        from io import StringIO

        async def run():
            self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            captured = StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                print("測試輸出")
            finally:
                sys.stdout = old_stdout

            assert captured.getvalue() == "測試輸出\n"

        asyncio.run(run())

    def test_bglog_shows_output(self):
        """測試 /bglog 顯示背景任務輸出"""

        async def run():
            self.handle_command(
                "/bg 說 hello",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            await asyncio.sleep(0.1)

            bglog = self.handle_command(
                "/bglog 10",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            assert bglog is not None
            assert "背景任務輸出" in bglog
            assert "#1" in bglog

        asyncio.run(run())

    def test_bglog_requires_n(self):
        """測試 /bglog 需要參數"""

        async def run():
            result = self.handle_command(
                "/bglog",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )
            assert "用法" in result
            assert "bglog" in result

        asyncio.run(run())

    def test_command_added_to_history(self):
        """測試 /指令 也會加入 history"""

        async def run():
            await self.agent.run("說 hi")

            self.handle_command(
                "/list",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            self.handle_command(
                "/now",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            self.handle_command(
                "/help",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            history = self.handle_command(
                "/history 10",
                self.current_session_id,
                self.current_agent_id,
                self.current_agent,
                self.client,
                self.config,
                None,
                self.db,
                self.pending_tasks,
                self.task_counter,
                self.bg_outputs,
            )

            assert history is not None
            assert "說 hi" in history
            assert "/list" in history
            assert "/now" in history
            assert "/help" in history

        asyncio.run(run())


class TestMockClient:
    """Mock 客戶端測試"""

    def setup_method(self):
        self.client = MockClient()

    @pytest.mark.asyncio
    async def test_mock_returns_quickly(self):
        """測試 mock 回應快速"""
        import time
        start = time.time()
        result = await self.client.generate("test", "")
        elapsed = time.time() - start
        assert result == "Mock response"
        assert elapsed < 0.1


needs_llm = pytest.mark.skipif(
    os.environ.get("TEST_LLM", "").lower() not in ("1", "true", "yes"),
    reason="LLM tests require TEST_LLM=1 environment variable"
)


@needs_llm
class TestWithLLM:
    """需要真實 LLM 的測試"""

    def setup_method(self):
        self.config = load_config_from_env()
        if not self.config.api_key:
            pytest.skip("No NVIDIA API key")
        self.client = NVIDIAClient(self.config)
        self.db = Database.get_instance()

    def teardown_method(self):
        self.db.clear_session("test_llm_bg")
        self.db.clear_session("test_llm_history")

    @pytest.mark.asyncio
    async def test_bg_with_real_llm_saves_to_history(self):
        """測試 /bg 在真實 LLM 下存入歷史"""
        self.db.clear_session("test_llm_bg")

        agent = Code5Agent(
            client=self.client,
            config=self.config,
            session_id="test_llm_bg",
            agent_id="root",
        )

        agent.memory.update("/bg 測試真實 LLM", "", None)
        await agent.run("說 hi")

        questions = self.db.get_user_conversations("test_llm_bg", "root")
        assert "/bg 測試真實 LLM" in questions, f"Expected /bg in history, got: {questions}"

        await self.client.close()

    @pytest.mark.asyncio
    async def test_real_conversation_saves_to_history(self):
        """測試真實對話存入歷史"""
        self.db.clear_session("test_llm_history")

        agent = Code5Agent(
            client=self.client,
            config=self.config,
            session_id="test_llm_history",
            agent_id="root",
        )

        await agent.run("說 hi")
        await agent.run("今天日期")

        convs = self.db.get_conversations("test_llm_history", "root")
        assert len(convs) >= 2, f"Expected at least 2 conversations, got {len(convs)}"
        assert convs[0]["role"] == "user"
        assert convs[0]["content"] == "說 hi"

        await self.client.close()

