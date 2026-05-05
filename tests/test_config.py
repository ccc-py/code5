"""Tests for config module."""

import os
from pathlib import Path

import pytest

from code5.config import DEFAULT_CONFIG, Config, SessionConfig, load_config_from_env


class TestConfig:
    def test_default_config(self) -> None:
        config = Config()
        assert config.model == "minimaxai/minimax-m2.7"
        assert config.max_turns == 10
        assert config.use_mock is False

    def test_custom_config(self) -> None:
        config = Config(
            api_key="test-key",
            model="custom-model",
            max_turns=5,
        )
        assert config.api_key == "test-key"
        assert config.model == "custom-model"
        assert config.max_turns == 5

    def test_workspace_creation(self, tmp_path: Path) -> None:
        workspace = tmp_path / "test_workspace"
        config = Config(workspace=workspace)
        assert config.workspace == workspace.resolve()
        assert workspace.exists()

    def test_is_configured_false_when_no_api_key(self) -> None:
        config = Config(api_key="", use_mock=False)
        assert config.is_configured is False

    def test_is_configured_true_when_has_api_key(self) -> None:
        config = Config(api_key="nvapi-xxx", use_mock=False)
        assert config.is_configured is True

    def test_is_configured_false_when_mock(self) -> None:
        config = Config(api_key="nvapi-xxx", use_mock=True)
        assert config.is_configured is False


class TestSessionConfig:
    def test_default_session_config(self) -> None:
        config = SessionConfig()
        assert config.session_id == "default"
        assert config.conversation_history == []
        assert config.key_info == []

    def test_custom_session_config(self) -> None:
        config = SessionConfig(
            session_id="test-session",
            conversation_history=["<user>hello</user>"],
        )
        assert config.session_id == "test-session"
        assert len(config.conversation_history) == 1


class TestLoadConfigFromEnv:
    def test_load_config_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_MODEL", raising=False)
        monkeypatch.delenv("CODE5_USE_MOCK", raising=False)

        config = load_config_from_env()
        assert config.api_key == ""
        assert config.use_mock is False

    def test_load_config_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NVIDIA_API_KEY", "env-api-key")
        monkeypatch.setenv("NVIDIA_MODEL", "env-model")
        monkeypatch.setenv("CODE5_USE_MOCK", "true")

        config = load_config_from_env()
        assert config.api_key == "env-api-key"
        assert config.model == "env-model"
        assert config.use_mock is True


class TestDefaultConfig:
    def test_default_config_singleton(self) -> None:
        assert DEFAULT_CONFIG.model == "minimaxai/minimax-m2.7"
        assert DEFAULT_CONFIG.api_key == ""
