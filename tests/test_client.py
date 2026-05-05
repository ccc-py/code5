"""Tests for client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from code5.client import LLMClient, MockClient, NVIDIAClient, create_client
from code5.config import Config


class TestMockClient:
    @pytest.mark.asyncio
    async def test_mock_client_default_response(self) -> None:
        client = MockClient(default_response="Hello!")
        result = await client.generate("any prompt")
        assert result == "Hello!"

    @pytest.mark.asyncio
    async def test_mock_client_keyword_response(self) -> None:
        client = MockClient(
            responses={"hello": "Hi there!"},
            default_response="Default",
        )
        result = await client.generate("say hello to me")
        assert result == "Hi there!"

    @pytest.mark.asyncio
    async def test_mock_client_case_insensitive(self) -> None:
        client = MockClient(responses={"hello": "Hi!"})
        result = await client.generate("HELLO world")
        assert result == "Hi!"

    @pytest.mark.asyncio
    async def test_mock_client_records_prompt(self) -> None:
        client = MockClient()
        await client.generate("test prompt")
        assert client.last_prompt == "test prompt"
        assert client.call_count == 1

    @pytest.mark.asyncio
    async def test_mock_client_add_response(self) -> None:
        client = MockClient()
        client.add_response("new_key", "new_response")
        result = await client.generate("new_key test")
        assert result == "new_response"

    @pytest.mark.asyncio
    async def test_mock_client_clear_responses(self) -> None:
        client = MockClient(responses={"key": "value"})
        client.clear_responses()
        result = await client.generate("any prompt")
        assert result == "Mock response"
        assert client.call_count == 1

    @pytest.mark.asyncio
    async def test_mock_client_reset(self) -> None:
        client = MockClient()
        await client.generate("prompt1")
        await client.generate("prompt2")
        client.reset()
        assert client.call_count == 0
        assert client.last_prompt == ""


class TestNVIDIAClient:
    @pytest.mark.asyncio
    async def test_nvidia_client_requires_api_key(self) -> None:
        config = Config(api_key="", use_mock=False)
        client = NVIDIAClient(config)
        with pytest.raises(ValueError, match="API key not configured"):
            await client.generate("test")

    @pytest.mark.asyncio
    async def test_nvidia_client_context_manager(self) -> None:
        config = Config(api_key="test-key")
        async with NVIDIAClient(config) as client:
            assert client.config.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_nvidia_client_network_error(self) -> None:
        config = Config(api_key="test-key")
        client = NVIDIAClient(config)

        try:
            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_post.side_effect = aiohttp.ClientError("Network error")

                with pytest.raises(RuntimeError, match="Network error"):
                    await client.generate("test prompt")
        finally:
            await client.close()


class TestCreateClient:
    def test_create_client_mock_mode(self) -> None:
        config = Config(use_mock=True)
        client = create_client(config)
        assert isinstance(client, MockClient)

    def test_create_client_no_api_key(self) -> None:
        config = Config(api_key="", use_mock=False)
        client = create_client(config)
        assert isinstance(client, MockClient)

    def test_create_client_with_api_key(self) -> None:
        config = Config(api_key="nvapi-xxx", use_mock=False)
        client = create_client(config)
        assert isinstance(client, NVIDIAClient)

    def test_create_client_with_responses(self) -> None:
        config = Config(use_mock=True, mock_responses={"key": "value"})
        client = create_client(config)
        assert isinstance(client, MockClient)
