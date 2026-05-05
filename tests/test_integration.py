"""整合測試 - 使用真實 LLM"""

import asyncio

import pytest

from code5.agent import Code5Agent
from code5.client import create_client
from code5.config import Config


def get_real_config() -> Config:
    """取得真實設定，若無 API key 则跳過測試"""
    config = Config()
    if not config.api_key:
        pytest.skip("NVIDIA_API_KEY not set, skipping real LLM test")
    return config


@pytest.mark.asyncio
async def test_llm_multiple_commands() -> None:
    """測試 LLM - 連續三句指令"""
    config = get_real_config()
    client = create_client(config)
    agent = Code5Agent(client=client, config=config)

    try:
        # 第一句
        response1 = await agent.run("你好")
        assert len(response1) > 0
        print(f"1. 你好 -> {response1[:100]}...")

        # 第二句
        response2 = await agent.run("寫一個 hello.py")
        assert len(response2) > 0
        print(f"2. 寫一個 hello.py -> {response2[:100]}...")

        # 第三句
        response3 = await agent.run("寫一個 factorial.c")
        assert len(response3) > 0
        print(f"3. 寫一個 factorial.c -> {response3[:100]}...")

    finally:
        if hasattr(client, 'close'):
            await client.close()
