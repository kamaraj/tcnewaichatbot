"""
Factory for creating LLM providers.
Enables easy switching between providers via configuration.
"""

from .base import BaseLLMProvider
from .ollama_provider import OllamaProvider
from .claude_provider import ClaudeProvider
from ..config import settings


def get_llm_provider(provider: str = None) -> BaseLLMProvider:
    """
    Factory function to get the configured LLM provider.
    
    Args:
        provider: Override the configured provider (ollama, claude, qwen)
        
    Returns:
        Configured LLM provider instance
    """
    provider_name = provider or settings.llm_provider
    
    if provider_name == "ollama":
        return OllamaProvider()
    elif provider_name == "claude":
        return ClaudeProvider()
    elif provider_name == "qwen":
        # Qwen can use Ollama if running locally, or API
        # For now, default to Ollama with qwen model
        return OllamaProvider(model="qwen:7b")
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


async def check_llm_status() -> dict:
    """Check the status of the configured LLM provider."""
    try:
        provider = get_llm_provider()
        is_healthy = await provider.health_check()
        
        return {
            "provider": settings.llm_provider,
            "model": getattr(provider, "model", "unknown"),
            "status": "healthy" if is_healthy else "unavailable",
            "message": "LLM is ready" if is_healthy else "LLM is not available. Please check your configuration."
        }
    except Exception as e:
        return {
            "provider": settings.llm_provider,
            "status": "error",
            "message": str(e)
        }
