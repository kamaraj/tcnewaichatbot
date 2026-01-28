"""
Gemini LLM Provider.
Connects to Google Gemini API (Vertex AI / Generative AI).
"""

import httpx
import json
from typing import AsyncGenerator, Optional
from .base import BaseLLMProvider
from ..config import settings


class GeminiProvider(BaseLLMProvider):
    """Gemini provider for Google Generative AI API inference."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.raw_api_key = api_key or settings.gemini_api_key
        # Support multiple keys (comma separated)
        if "," in self.raw_api_key:
            self.api_keys = [k.strip() for k in self.raw_api_key.split(",") if k.strip()]
        else:
            self.api_keys = [self.raw_api_key]
            
        self.current_key_index = 0
        self.model = model or settings.gemini_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        
        if not self.api_keys:
            print("Warning: Gemini API Key is missing.")

    def _get_current_key(self):
        return self.api_keys[self.current_key_index]
        
    def _rotate_key(self):
        """Rotate to the next available API key."""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            print(f"Switching to Gemini API Key #{self.current_key_index + 1}")

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using Gemini with Key Rotation."""
        
        full_message = self.build_rag_prompt(prompt, context)
        
        payload = {
            "contents": [{
                "parts": [{"text": full_message}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Try up to 2x the number of keys to ensure full rotation + 1 retry
            max_attempts = len(self.api_keys) * 2
            
            for attempt in range(max_attempts):
                current_key = self._get_current_key()
                url = f"{self.base_url}/models/{self.model}:generateContent?key={current_key}"
                
                try:
                    response = await client.post(url, json=payload)
                    
                    if response.status_code == 429:
                        print(f"Gemini 429 Rate Limit on Key #{self.current_key_index + 1}")
                        self._rotate_key()
                        import asyncio
                        await asyncio.sleep(1) # Brief pause before trying next key
                        continue
                        
                    response.raise_for_status()
                    result = response.json()
                    
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            return "".join([part.get("text", "") for part in candidate["content"]["parts"]])
                    return ""
                    
                except httpx.HTTPError as e:
                    is_rate_limit = False
                    if hasattr(e, 'response') and e.response:
                         if e.response.status_code == 429:
                             is_rate_limit = True
                             
                    if is_rate_limit:
                        print(f"Gemini 429 (HTTPError) on Key #{self.current_key_index + 1}")
                        self._rotate_key()
                        import asyncio
                        await asyncio.sleep(1)
                        continue
                            
                    error_msg = f"Gemini request failed: {str(e)}"
                    if hasattr(e, 'response') and e.response:
                        error_msg += f" - {e.response.text}"
                    
                    # If it's the last attempt, raise
                    if attempt == max_attempts - 1:
                        raise RuntimeError(error_msg)
                        
        raise RuntimeError("All Gemini API keys exhausted.")

    async def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Stream a response from Gemini."""
        
        full_message = self.build_rag_prompt(prompt, context)
        
        # Note: Gemini SSE uses streamGenerateContent?alt=sse
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_message}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            line = line.strip()
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if "candidates" in data and len(data["candidates"]) > 0:
                                        candidate = data["candidates"][0]
                                        if "content" in candidate and "parts" in candidate["content"]:
                                            for part in candidate["content"]["parts"]:
                                                if "text" in part:
                                                    yield part["text"]
                                except json.JSONDecodeError:
                                    continue
            except httpx.HTTPError as e:
                error_msg = f"Gemini request failed: {str(e)}"
                yield f"\n\nError: {error_msg}"

    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        if not self.api_key:
            return False
            
        # Try to list models or just a simple check
        url = f"{self.base_url}/models?key={self.api_key}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return True
                return False
            except Exception:
                return False
