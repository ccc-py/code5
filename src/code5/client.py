"""LLM Client implementations for code5.

This module provides:
- NVIDIAClient: Real client using NVIDIA NIM API
- MockClient: Testing client that returns predefined responses
"""

from abc import ABC, abstractmethod

import aiohttp

from .config import Config


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system: System prompt (optional)

        Returns:
            The LLM response as a string
        """
        raise NotImplementedError


class NVIDIAClient(LLMClient):
    """Client for NVIDIA NIM API (OpenAI-compatible)."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.model = config.model
        self.base_url = config.base_url
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def generate(self, prompt: str, system: str = "") -> str:
        if not self.config.api_key:
            raise ValueError("NVIDIA API key not configured. Set NVIDIA_API_KEY or use MockClient.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }

        try:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"NVIDIA API error {resp.status}: {error_text}")
                result = await resp.json()
                return result["choices"][0]["message"]["content"].strip()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Network error calling NVIDIA API: {e}") from e

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "NVIDIAClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


class MockClient(LLMClient):
    """Mock client for testing - returns predefined responses."""

    def __init__(self, responses: dict[str, str] | None = None, default_response: str = "Mock response") -> None:
        self.responses = responses or {}
        self.default_response = default_response
        self.call_count = 0
        self.last_prompt = ""
        self.last_system = ""

    async def generate(self, prompt: str, system: str = "") -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system = system

        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response

        return self.default_response

    def add_response(self, key: str, response: str) -> None:
        self.responses[key] = response

    def clear_responses(self) -> None:
        self.responses.clear()
        self.call_count = 0

    def reset(self) -> None:
        self.call_count = 0
        self.last_prompt = ""
        self.last_system = ""


def create_client(config: Config) -> LLMClient:
    """Factory function to create an LLM client based on configuration.

    Args:
        config: Configuration object

    Returns:
        An LLMClient instance (NVIDIAClient or MockClient)
    """
    if config.use_mock or not config.api_key:
        if config.mock_responses:
            return MockClient(responses=config.mock_responses)
        return MockClient()

    return NVIDIAClient(config)
