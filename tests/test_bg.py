"""測試背景執行功能"""

import asyncio

import pytest

from code5 import Code5Agent, MockClient
from code5.config import load_config_from_env


class TestBackgroundExecution:
    """測試 /bg 背景執行"""

    def setup_method(self):
        self.config = load_config_from_env()
        self.config.use_mock = True
        self.client = MockClient()

    def teardown_method(self):
        from code5.db import Database
        db = Database.get_instance()
        db.clear_session("test_bg")

    @pytest.mark.asyncio
    async def test_bg_task_creates_successfully(self):
        """測試可以創建背景任務"""
        task = asyncio.create_task(asyncio.sleep(0.01))
        assert task is not None
        done, _ = await asyncio.wait([task], timeout=1.0)
        assert task in done

    @pytest.mark.asyncio
    async def test_mock_client_returns_quickly(self):
        """測試 MockClient 應該快速返回"""
        import time
        start = time.time()
        result = await self.client.generate("test", "")
        elapsed = time.time() - start
        assert result == "Mock response"
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_agent_run_saves_to_history(self):
        """測試 agent.run 會保存到歷史記錄"""
        from code5.db import Database
        db = Database.get_instance()
        db.clear_session("test_history")

        agent = Code5Agent(
            client=self.client,
            config=self.config,
            session_id="test_history",
            agent_id="root",
        )

        result = await agent.run("hello")
        assert result

        convs = db.get_conversations("test_history", "root")
        assert len(convs) >= 2
        assert convs[0]["role"] == "user"
        assert convs[0]["content"] == "hello"

        db.clear_session("test_history")

    @pytest.mark.asyncio
    async def test_build_context_limits_history(self):
        """測試 build_context() 會限制歷史長度"""
        from code5.db import Database
        db = Database.get_instance()
        db.clear_session("test_context")

        config = load_config_from_env()
        config.use_mock = True
        config.max_turns = 5

        agent = Code5Agent(
            client=self.client,
            config=config,
            session_id="test_context",
            agent_id="root",
        )

        for i in range(20):
            await agent.run(f"message {i}")

        context = agent.memory.build_context()
        user_count = context.count("<user>")
        assert user_count <= 5, f"Expected <= 5, got {user_count}"

        history_len = len(agent.memory.conversation.history)
        assert history_len == 40, f"Expected 40, got {history_len}"

        db.clear_session("test_context")


class TestMockClient:
    """測試 MockClient"""

    def setup_method(self):
        self.client = MockClient()

    @pytest.mark.asyncio
    async def test_mock_returns_default_response(self):
        result = await self.client.generate("any prompt", "")
        assert result == "Mock response"

    @pytest.mark.asyncio
    async def test_mock_with_keyword(self):
        self.client.add_response("hello", "Hello there!")
        result = await self.client.generate("say hello", "")
        assert result == "Hello there!"

    @pytest.mark.asyncio
    async def test_mock_case_insensitive(self):
        self.client.add_response("python", "Python is great!")
        result = await self.client.generate("Tell me about PYTHON", "")
        assert result == "Python is great!"
