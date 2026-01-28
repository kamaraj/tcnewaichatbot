"""
Base class for LLM providers.
Enables easy switching between Ollama, Claude, Qwen, etc.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User's question or full prompt
            context: Optional retrieved context from documents
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM.
        
        Args:
            prompt: User's question or full prompt
            context: Optional retrieved context from documents
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Response text chunks
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is available."""
        pass
    
    def build_rag_prompt(self, question: str, context: Optional[str] = None) -> str:
        """
        Build a concise RAG prompt focused on rulebook assistant persona.
        If context is missing, return the question as is (assume it's a full prompt).
        """
        if not context:
            return question
            
        return f"""### Instruction:
You are a helpful and strict IHSA Rulebook assistant. 
- Use ONLY the following information to answer the question.
- Do NOT mention "context", "documents", or "AI". 
- If the answer is not in the text, say you cannot find it.
- Maintain citations (Section ####, page ##) if they exist.

### Information:
{context}

### User Question:
{question}

### Assistant Response:"""
