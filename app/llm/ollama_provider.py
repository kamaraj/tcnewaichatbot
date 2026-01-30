"""
Ollama LLM Provider for local model inference.
Supports TinyLlama, Mistral, Phi, Qwen, and other Ollama models.
"""

import httpx
import json
from typing import AsyncGenerator, Optional
from .base import BaseLLMProvider
from ..config import settings


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM inference."""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = httpx.Timeout(120.0, connect=10.0)
    
    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using Ollama."""
        
        full_prompt = self.build_rag_prompt(prompt, context)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            except httpx.HTTPError as e:
                raise RuntimeError(f"Ollama request failed: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Stream a response from Ollama."""
        
        full_prompt = self.build_rag_prompt(prompt, context)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        }
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPError as e:
                yield f"\n\nError: Ollama request failed - {str(e)}"
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and the model is available."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False
                
                # Check if model is available
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                return self.model.split(":")[0] in model_names
            except Exception:
                return False
    
    async def list_models(self) -> list[str]:
        """List available models in Ollama."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                return [m.get("name", "") for m in models]
            except Exception:
                return []
