"""
OpenAI LLM Provider.
Connects to OpenAI API for models like GPT-4o, GPT-3.5-turbo, etc.
"""

import httpx
import json
from typing import AsyncGenerator, Optional
from .base import BaseLLMProvider
from ..config import settings


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for cloud API inference."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = "https://api.openai.com/v1"
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        
        if not self.api_key:
            print("Warning: OpenAI API Key is missing.")

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using OpenAI."""
        
        full_message = self.build_rag_prompt(prompt, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                error_msg = f"OpenAI request failed: {str(e)}"
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
        """Stream a response from OpenAI."""
        
        full_message = self.build_rag_prompt(prompt, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                error_msg = f"OpenAI request failed: {str(e)}"
                yield f"\n\nError: {error_msg}"

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        if not self.api_key:
            return False
            
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                # A simple models list check
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                if response.status_code == 200:
                    return True
                return False
            except Exception:
                return False
