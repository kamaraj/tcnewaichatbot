"""
OpenRouter LLM Provider.
Connects to openrouter.ai API for various models (GPT-4, Claude 3, etc).
"""

import httpx
import json
from typing import AsyncGenerator, Optional
from .base import BaseLLMProvider
from ..config import settings


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider for cloud API inference."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = httpx.Timeout(120.0, connect=10.0)
        
        if not self.api_key:
            print("Warning: OpenRouter API Key is missing.")

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using OpenRouter."""
        
        full_message = self.build_rag_prompt(prompt, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TCA AI Chatbot",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": full_message}
                        ],
                        "stream": False,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                return ""
                
            except httpx.HTTPError as e:
                error_msg = f"OpenRouter request failed: {str(e)}"
                if hasattr(e, 'response') and e.response:
                    error_msg += f" - {e.response.text}"
                raise RuntimeError(error_msg)

    async def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Stream a response from OpenRouter."""
        
        full_message = self.build_rag_prompt(prompt, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TCA AI Chatbot",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": full_message}
                        ],
                        "stream": True,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            line = line.strip()
                            if line.startswith("data: ") and line != "data: [DONE]":
                                try:
                                    data = json.loads(line[6:])
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            yield delta["content"]
                                except json.JSONDecodeError:
                                    continue
            except httpx.HTTPError as e:
                error_msg = f"OpenRouter request failed: {str(e)}"
                yield f"\n\nError: {error_msg}"

    async def health_check(self) -> bool:
        """Check if OpenRouter API is accessible."""
        if not self.api_key:
            return False
            
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            try:
                # We can't really "ping" easily without a cost, 
                # but we can try to list models or check a cheap endpoint.
                # OpenRouter doesn't have a simple 'ping'.
                # Let's try to fetch model info for the configured model.
                headers = {"Authorization": f"Bearer {self.api_key}"}
                # The /models endpoint is free
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                if response.status_code == 200:
                    return True
                return False
            except Exception:
                return False
