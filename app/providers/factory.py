"""Factory for creating LLM provider instances."""
from typing import Optional

from app.core.config import settings
from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider


def create_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMProvider:
    """
    Create an LLM provider instance.

    Args:
        provider_name: Name of provider (openai, ollama). If None, uses settings.default_llm_provider
        model: Model name (used to auto-detect provider if provider_name not given)

    Returns:
        BaseLLMProvider instance

    Raises:
        ValueError: If provider is unknown
    """
    provider_name = provider_name or settings.default_llm_provider

    # Auto-detect provider from model name if needed
    if not provider_name and model:
        if model.startswith("gpt-") or model.startswith("o1-"):
            provider_name = "openai"
        elif "/" in model or model in ["llama", "mistral", "codellama"]:
            provider_name = "ollama"

    provider_name = (provider_name or "openai").lower()

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base_url
        )
    elif provider_name == "ollama":
        return OllamaProvider(
            base_url=settings.local_llm_endpoint
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
