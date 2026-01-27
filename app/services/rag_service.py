"""
RAG Service - Orchestrates retrieval and generation.
"""

from typing import List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from .vector_store import VectorStore, SearchResult
from ..llm import get_llm_provider
from ..config import settings


@dataclass
class RAGResponse:
    """Response from the RAG pipeline."""
    answer: str
    sources: List[Dict[str, Any]]
    query: str


class RAGService:
    """Retrieval-Augmented Generation service."""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = get_llm_provider()
    
    def _format_context(self, results: List[SearchResult]) -> str:
        """Format search results into context for the LLM."""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.metadata.get("source", "Unknown source")
            context_parts.append(f"[{i}] {source}:\n{result.text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _extract_sources(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Extract source information from search results."""
        sources = []
        for result in results:
            sources.append({
                "filename": result.metadata.get("filename", "Unknown"),
                "page": result.metadata.get("page", 0),
                "relevance_score": round(result.score, 3),
                "excerpt": result.text[:200] + "..." if len(result.text) > 200 else result.text
            })
        return sources
    
    async def query(
        self,
        question: str,
        top_k: int = None,
        filter_doc_id: str = None
    ) -> RAGResponse:
        """
        Process a question through the RAG pipeline.
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            filter_doc_id: Optional filter to specific document
            
        Returns:
            RAGResponse with answer and sources
        """
        # Retrieve relevant chunks
        results = self.vector_store.search(
            query=question,
            top_k=top_k or settings.top_k_results,
            filter_doc_id=filter_doc_id
        )
        
        # Format context
        context = self._format_context(results)
        
        # Generate answer
        answer = await self.llm.generate(
            prompt=question,
            context=context
        )
        
        # Extract sources
        sources = self._extract_sources(results)
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            query=question
        )
    
    async def query_stream(
        self,
        question: str,
        top_k: int = None,
        filter_doc_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a response from the RAG pipeline.
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            filter_doc_id: Optional filter to specific document
            
        Yields:
            Chunks of the response and final sources
        """
        # Retrieve relevant chunks
        results = self.vector_store.search(
            query=question,
            top_k=top_k or settings.top_k_results,
            filter_doc_id=filter_doc_id
        )
        
        # Format context
        context = self._format_context(results)
        
        # Extract sources first (we'll send them at the end)
        sources = self._extract_sources(results)
        
        # Stream the answer
        async for chunk in self.llm.generate_stream(
            prompt=question,
            context=context
        ):
            yield {"type": "content", "content": chunk}
        
        # Send sources at the end
        yield {"type": "sources", "sources": sources}
        yield {"type": "done"}
