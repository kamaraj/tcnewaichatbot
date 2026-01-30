"""
Claude LLM Provider for Anthropic API.
For future use when switching from local Ollama to Claude.
"""

import httpx
import json
from typing import AsyncGenerator, Optional
from .base import BaseLLMProvider
from ..config import settings


class ClaudeProvider(BaseLLMProvider):
    """Claude provider for Anthropic API."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model
        self.base_url = "https://api.anthropic.com/v1"
        self.timeout = httpx.Timeout(120.0, connect=10.0)
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude provider")
    
    def _get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using Claude."""
        
        full_prompt = self.build_rag_prompt(prompt, context)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "user", "content": full_prompt}
                        ],
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract text from Claude's response format
                content = result.get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")
                return ""
            except httpx.HTTPError as e:
                raise RuntimeError(f"Claude request failed: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Stream a response from Claude."""
        
        full_prompt = self.build_rag_prompt(prompt, context)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "user", "content": full_prompt}
                        ],
                        "temperature": temperature,
                        "stream": True
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if "text" in delta:
                                        yield delta["text"]
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPError as e:
                yield f"\n\nError: Claude request failed - {str(e)}"
    
    async def health_check(self) -> bool:
        """Check if Claude API is accessible."""
        if not self.api_key:
            return False
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                # Simple check - try to make a minimal request
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json={
                        "model": self.model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}]
                    }
                )
                return response.status_code == 200
            except Exception:
                return False
