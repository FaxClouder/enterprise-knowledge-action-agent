from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Centralized runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Enterprise Knowledge & Action Agent"
    environment: Literal["dev", "test", "prod"] = "dev"

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    temperature: float = 0.1
    force_local_fallback: bool = Field(default=False, alias="FORCE_LOCAL_FALLBACK")

    kb_dir: Path = Field(default=ROOT_DIR / "data" / "knowledge_base")
    vector_store_dir: Path = Field(default=ROOT_DIR / "data" / "vector_store")
    memory_store_dir: Path = Field(default=ROOT_DIR / "data" / "memory_store")
    mcp_stub_file: Path = Field(default=ROOT_DIR / "data" / "mcp_stub" / "resources.json")

    langsmith_tracing: bool = Field(default=True, alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(default="enterprise-agent", alias="LANGSMITH_PROJECT")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")

    mcp_server_name: str = Field(default="filesystem", alias="MCP_SERVER_NAME")
    mcp_server_command: str | None = Field(default=None, alias="MCP_SERVER_COMMAND")
    mcp_server_args: str = Field(default="", alias="MCP_SERVER_ARGS")

    retrieval_top_k: int = 4
    retrieval_max_retries: int = 2
    retrieval_score_threshold: float = 0.18

    def ensure_runtime_dirs(self) -> None:
        """Create runtime directories if they do not already exist."""
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.memory_store_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_stub_file.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
