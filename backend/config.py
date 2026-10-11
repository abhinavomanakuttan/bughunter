"""
BugHunter — Unified configuration management.
Reads from environment variables with sensible defaults.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BugHunterSettings(BaseSettings):
    """All configuration for BugHunter read from environment variables."""

    # LLM provider selection: openai | gemini | ollama
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", alias="GEMINI_MODEL")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # Scanner defaults
    default_max_depth: int = Field(default=3, alias="DEFAULT_MAX_DEPTH")
    default_browser: str = Field(default="chromium", alias="DEFAULT_BROWSER")
    default_headless: bool = Field(default=True, alias="DEFAULT_HEADLESS")
    max_actions: int = Field(default=100, alias="MAX_ACTIONS")
    scan_timeout_seconds: int = Field(default=300, alias="SCAN_TIMEOUT_SECONDS")

    # Security
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        alias="ALLOWED_ORIGINS",
    )

    # Storage
    reports_dir: Path = Field(default=Path("reports"), alias="REPORTS_DIR")
    db_path: Path = Field(default=Path("bughunter.db"), alias="DB_PATH")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Demo mode — allows scanning localhost without SSRF check
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True, extra="ignore")


@lru_cache
def get_settings() -> BugHunterSettings:
    """Return the singleton settings instance (loads from .env)."""
    return BugHunterSettings()
