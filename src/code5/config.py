"""Configuration management for code5."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Main configuration for code5 agent."""

    api_key: str = ""
    model: str = "minimaxai/minimax-m2.7"
    base_url: str = "https://integrate.api.nvidia.com/v1"
    max_turns: int = 10
    max_history: int = 40
    workspace: Path = field(default_factory=lambda: Path("~/.code5").expanduser())
    use_mock: bool = False
    mock_responses: dict[str, str] | None = None
    shell_timeout: int = 30
    review_enabled: bool = True
    allow_outside_access: bool = False

    def __post_init__(self) -> None:
        self.workspace = Path(self.workspace).expanduser().resolve()
        if not self.workspace.exists():
            self.workspace.mkdir(parents=True, exist_ok=True)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key) and not self.use_mock


@dataclass
class SessionConfig:
    """Configuration for a session."""

    session_id: str = "default"
    conversation_history: list[str] = field(default_factory=list)
    key_info: list[str] = field(default_factory=list)
    outside_access_granted: set[str] = field(default_factory=set)


def load_config_from_env() -> Config:
    """Load configuration from environment variables."""
    import os

    api_key = os.environ.get("NVIDIA_API_KEY", "")
    model = os.environ.get("NVIDIA_MODEL", "minimaxai/minimax-m2.7")
    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    use_mock = os.environ.get("CODE5_USE_MOCK", "false").lower() == "true"

    return Config(
        api_key=api_key,
        model=model,
        base_url=base_url,
        use_mock=use_mock,
    )


DEFAULT_CONFIG = Config()
