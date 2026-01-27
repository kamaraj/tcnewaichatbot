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
        context: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User's question
            context: Retrieved context from documents
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
        context: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM.
        
        Args:
            prompt: User's question
            context: Retrieved context from documents
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
    
    def build_rag_prompt(self, question: str, context: str) -> str:
        """
        Build a RAG prompt with context and question.
        Uses Evidence-First approach for better results with smaller models.
        """
        return f"""You are a helpful assistant that answers questions based ONLY on the provided context.

CONTEXT FROM DOCUMENTS:
{context}

INSTRUCTIONS:
1. Answer the question using ONLY the information from the context above
2. If the answer is not found in the context, say "I couldn't find this information in the uploaded documents."
3. Always cite which part of the document your answer comes from
4. Be concise and accurate
5. Do NOT make up information that is not in the context

QUESTION: {question}

ANSWER:"""
