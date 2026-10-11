"""
BugHunter — Configurable LLM service.
Supports OpenAI, Google Gemini, and Ollama with a unified async interface.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LLMService:
    """
    Unified LLM service supporting OpenAI, Gemini, and Ollama.
    Returns OpenAI-compatible AsyncOpenAI client for most use cases.
    """

    def __init__(self, provider: str = "openai", **kwargs: Any) -> None:
        self._provider = provider.lower()
        self._kwargs = kwargs

    def get_openai_client(self) -> Any:
        """Get an OpenAI-compatible async client based on provider configuration."""
        from backend.config import get_settings
        settings = get_settings()

        if self._provider == "gemini":
            # Use OpenAI-compatible Gemini endpoint
            try:
                from openai import AsyncOpenAI
                if not settings.gemini_api_key:
                    raise ValueError("GEMINI_API_KEY not set")
                client = AsyncOpenAI(
                    api_key=settings.gemini_api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                )
                logger.info("Using Gemini provider via OpenAI-compatible endpoint")
                return client
            except ImportError:
                logger.error("openai package not installed")
                raise

        elif self._provider == "ollama":
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    api_key="ollama",
                    base_url=f"{settings.ollama_base_url}/v1",
                )
                logger.info("Using Ollama provider: %s", settings.ollama_base_url)
                return client
            except ImportError:
                logger.error("openai package not installed")
                raise

        else:  # openai (default)
            try:
                from openai import AsyncOpenAI
                if not settings.openai_api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("Using OpenAI provider")
                return client
            except ImportError:
                logger.error("openai package not installed")
                raise

    def get_model_name(self) -> str:
        """Get the model name for the configured provider."""
        from backend.config import get_settings
        settings = get_settings()

        if self._provider == "gemini":
            return settings.gemini_model
        elif self._provider == "ollama":
            return settings.ollama_model
        else:
            return settings.openai_model

    async def chat_complete(self, messages: list[dict], temperature: float = 0) -> str:
        """
        Unified chat completion that works across providers.
        Returns the assistant message content string.
        """
        from backend.config import get_settings
        settings = get_settings()

        # Try Gemini native SDK first if provider is gemini
        if self._provider == "gemini" and settings.gemini_api_key:
            try:
                return await self._gemini_native(messages)
            except Exception as exc:
                logger.warning("Gemini native SDK failed, falling back to OpenAI compat: %s", exc)

        client = self.get_openai_client()
        model = self.get_model_name()

        response = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def _gemini_native(self, messages: list[dict]) -> str:
        """Use google-genai native SDK for Gemini."""
        from backend.config import get_settings
        settings = get_settings()
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            # Convert to Gemini format
            combined = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=combined
            )
            return response.text
        except ImportError:
            raise ImportError("google-genai not installed")


def get_llm_service() -> LLMService:
    """Get configured LLM service from settings."""
    from backend.config import get_settings
    settings = get_settings()
    return LLMService(provider=settings.llm_provider)
