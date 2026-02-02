"""
Lightweight Vector Service for Vercel Serverless.
Uses NumPy for similarity search instead of ChromaDB to reduce package size.
"""
import os
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx

# Cache for loaded data
_vector_data = None
_embeddings_matrix = None


@dataclass
class SearchResult:
    """Represents a search result from the vector store."""
    text: str
    metadata: Dict[str, Any]
    score: float


def _load_vector_data():
    """Load the pre-computed vector index."""
    global _vector_data, _embeddings_matrix
    
    if _vector_data is not None:
        return _vector_data, _embeddings_matrix
    
    # Try to find the vector index file
    index_path = Path("data/vector_index.pkl")
    if not index_path.exists():
        index_path = Path("/var/task/data/vector_index.pkl")  # Vercel path
    
    if not index_path.exists():
        print(f"⚠️ Vector index not found at {index_path}")
        return None, None
    
    with open(index_path, 'rb') as f:
        _vector_data = pickle.load(f)
    
    # Convert embeddings to numpy matrix
    if _vector_data.get('embeddings'):
        _embeddings_matrix = np.array(_vector_data['embeddings'])
    
    print(f"✅ Loaded {len(_vector_data.get('documents', []))} documents from vector index")
    return _vector_data, _embeddings_matrix


def get_embedding_from_openai(text: str, api_key: str) -> List[float]:
    """Get embedding using OpenAI API directly (no LangChain dependency)."""
    response = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "input": text,
            "model": "text-embedding-3-large"
        },
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def cosine_similarity(query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and documents."""
    # Normalize vectors
    query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
    doc_norms = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=1, keepdims=True) + 1e-10)
    
    # Compute cosine similarity
    similarities = np.dot(doc_norms, query_norm)
    return similarities


def search_serverless(query: str, api_key: str, top_k: int = 10) -> List[SearchResult]:
    """
    Perform vector similarity search using pre-computed embeddings.
    Uses OpenAI API directly for query embedding.
    """
    vector_data, embeddings_matrix = _load_vector_data()
    
    if vector_data is None or embeddings_matrix is None:
        print("❌ Vector data not loaded")
        return []
    
    # Get query embedding from OpenAI
    try:
        query_embedding = np.array(get_embedding_from_openai(query, api_key))
    except Exception as e:
        print(f"❌ Failed to get embedding: {e}")
        return []
    
    # Compute similarities
    similarities = cosine_similarity(query_embedding, embeddings_matrix)
    
    # Get top-k results
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # Build results
    results = []
    documents = vector_data.get('documents', [])
    metadatas = vector_data.get('metadatas', [])
    
    for idx in top_indices:
        score = float(similarities[idx])
        
        # Apply confidence boost for display
        boosted_score = score
        if score > 0.4:
            boosted_score = 0.6 + (score - 0.4) * (0.38 / 0.5)
        
        results.append(SearchResult(
            text=documents[idx] if idx < len(documents) else "",
            metadata=metadatas[idx] if idx < len(metadatas) else {},
            score=min(0.99, max(0.01, boosted_score))
        ))
    
    return results


class ServerlessVectorStore:
    """Wrapper class to provide ChromaDB-like interface for serverless deployment."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self._load_data()
    
    def _load_data(self):
        """Load vector data on initialization."""
        _load_vector_data()
    
    def similarity_search(self, query: str, k: int = 10):
        """Search for similar documents - returns list of Document-like objects."""
        results = search_serverless(query, self.api_key, top_k=k)
        
        # Convert to LangChain Document-like format
        class MockDocument:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata
        
        return [MockDocument(r.text, r.metadata) for r in results]
