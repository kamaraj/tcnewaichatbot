"""
Vector Store Service using NumPy.
Lightweight vector store with Ollama embeddings.
No PyTorch or ONNX runtime required.
"""

import json
import pickle
import numpy as np
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from ..config import settings
from .pdf_processor import DocumentChunk, ProcessedDocument


@dataclass
class SearchResult:
    """Represents a search result from the vector store."""
    text: str
    metadata: Dict[str, Any]
    score: float


@dataclass
class StoredDocument:
    """A document stored in the vector store."""
    chunk_id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]


class VectorStore:
    """NumPy-based vector store for document embeddings.
    
    Uses Ollama for embeddings and NumPy for similarity search.
    No heavy dependencies like PyTorch or ONNX runtime needed.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for vector store."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Store documents in memory with persistence
        self._documents: List[StoredDocument] = []
        self._embeddings: Optional[np.ndarray] = None
        
        # Persistence path
        self._persist_dir = Path(settings.chroma_persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._persist_dir / "vector_store.pkl"
        
        # Ollama settings
        self._ollama_url = settings.ollama_base_url
        self._embedding_model = settings.embedding_model
        
        # Load existing data
        self._load()
        
        self._initialized = True
        print(f"Using Ollama for embeddings: {self._embedding_model}")
        print(f"Vector store initialized. Collection has {len(self._documents)} documents.")
    
    def _load(self):
        """Load persisted data from disk."""
        if self._data_file.exists():
            try:
                with open(self._data_file, 'rb') as f:
                    data = pickle.load(f)
                    self._documents = data.get('documents', [])
                    embeddings = data.get('embeddings')
                    if embeddings is not None:
                        self._embeddings = np.array(embeddings)
                print(f"Loaded {len(self._documents)} documents from disk.")
            except Exception as e:
                print(f"Error loading data: {e}")
                self._documents = []
                self._embeddings = None
    
    def _save(self):
        """Persist data to disk."""
        try:
            data = {
                'documents': self._documents,
                'embeddings': self._embeddings.tolist() if self._embeddings is not None else None
            }
            with open(self._data_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text using Ollama."""
        response = httpx.post(
            f"{self._ollama_url}/api/embeddings",
            json={
                "model": self._embedding_model,
                "prompt": text
            },
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using Ollama."""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings
    async def embed_text_async(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """Generate embedding for a single text using Ollama asynchronously."""
        response = await client.post(
            f"{self._ollama_url}/api/embeddings",
            json={
                "model": self._embedding_model,
                "prompt": text
            },
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()["embedding"]

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in parallel using Ollama.
        Uses a semaphore to limit concurrency.
        """
        semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests
        
        async def semi_safe_embed(client, text):
            async with semaphore:
                return await self.embed_text_async(client, text)
        
        timeout = httpx.Timeout(120.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [semi_safe_embed(client, text) for text in texts]
            return await asyncio.gather(*tasks)

    async def add_document_async(self, doc: ProcessedDocument) -> Dict[str, Any]:
        """
        Add a processed document to the vector store asynchronously.
        
        Args:
            doc: ProcessedDocument with chunks
            
        Returns:
            Summary of the indexing operation
        """
        if not doc.chunks:
            return {"status": "error", "message": "No chunks to index"}
        
        # Generate embeddings for all chunks in parallel
        texts = [chunk.text for chunk in doc.chunks]
        embeddings = await self.embed_texts_async(texts)
        
        # Create stored documents
        new_docs = []
        for chunk, embedding in zip(doc.chunks, embeddings):
            stored_doc = StoredDocument(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata
            )
            new_docs.append(stored_doc)
        
        # Add to collection
        self._documents.extend(new_docs)
        
        # Update embeddings matrix
        new_embeddings = np.array(embeddings)
        if self._embeddings is None:
            self._embeddings = new_embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, new_embeddings])
        
        # Persist changes
        self._save()
        
        return {
            "status": "success",
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "chunks_indexed": len(new_docs),
            "total_documents": len(self._documents)
        }

    def _cosine_similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and documents."""
        # Normalize vectors
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        
        # Compute cosine similarity
        similarities = np.dot(doc_norms, query_norm)
        return similarities
    
    def add_document(self, doc: ProcessedDocument) -> Dict[str, Any]:
        """
        Add a processed document to the vector store.
        
        Args:
            doc: ProcessedDocument with chunks
            
        Returns:
            Summary of the indexing operation
        """
        if not doc.chunks:
            return {"status": "error", "message": "No chunks to index"}
        
        # Generate embeddings for all chunks
        texts = [chunk.text for chunk in doc.chunks]
        embeddings = self.embed_texts(texts)
        
        # Create stored documents
        new_docs = []
        for chunk, embedding in zip(doc.chunks, embeddings):
            stored_doc = StoredDocument(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata
            )
            new_docs.append(stored_doc)
        
        # Add to collection
        self._documents.extend(new_docs)
        
        # Update embeddings matrix
        new_embeddings = np.array(embeddings)
        if self._embeddings is None:
            self._embeddings = new_embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, new_embeddings])
        
        # Persist changes
        self._save()
        
        return {
            "status": "success",
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "chunks_indexed": len(new_docs),
            "total_documents": len(self._documents)
        }
    
    def search(
        self,
        query: str,
        top_k: int = None,
        filter_doc_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filter_doc_id: Optional filter by document ID
            
        Returns:
            List of SearchResult objects
        """
        top_k = top_k or settings.top_k_results
        
        if not self._documents or self._embeddings is None:
            return []
        
        # Generate query embedding
        query_embedding = np.array(self.embed_text(query))
        
        # Filter documents if needed
        if filter_doc_id:
            indices = [i for i, doc in enumerate(self._documents) 
                      if doc.metadata.get("doc_id") == filter_doc_id]
            if not indices:
                return []
            filtered_embeddings = self._embeddings[indices]
            filtered_docs = [self._documents[i] for i in indices]
        else:
            filtered_embeddings = self._embeddings
            filtered_docs = self._documents
        
        # Compute similarities
        similarities = self._cosine_similarity(query_embedding, filtered_embeddings)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            doc = filtered_docs[idx]
            # Apply a confidence boost to the score for better UI display
            # This makes reasonably good matches feel more 'confident'
            raw_score = float(similarities[idx])
            boosted_score = raw_score
            if raw_score > 0.4:
                # Scale from [0.4, 0.9] to [0.6, 0.98]
                boosted_score = 0.6 + (raw_score - 0.4) * (0.38 / 0.5)
            
            results.append(SearchResult(
                text=doc.text,
                metadata=doc.metadata,
                score=min(0.99, max(0.01, boosted_score))
            ))
        
        return results
    
    def search_by_metadata(self, filters: Dict[str, Any], limit: int = 10) -> List[SearchResult]:
        """Search documents by metadata filters."""
        if not self._documents:
            return []
            
        results = []
        for doc in self._documents:
            match = True
            for key, value in filters.items():
                if key not in doc.metadata:
                    match = False
                    break
                
                # Support list membership for topic_tags
                if isinstance(doc.metadata[key], list) and not isinstance(value, list):
                    if value not in doc.metadata[key]:
                        match = False
                        break
                elif doc.metadata[key] != value:
                    # Support range for section_id
                    if key == "section_id" and isinstance(value, tuple) and len(value) == 2:
                         if doc.metadata[key] is None or not (value[0] <= doc.metadata[key] <= value[1]):
                             match = False
                             break
                    else:
                        match = False
                        break
            
            if match:
                results.append(SearchResult(
                    text=doc.text,
                    metadata=doc.metadata,
                    score=1.0 # Exact metadata match
                ))
                if len(results) >= limit:
                    break
                    
        return results

    def keyword_scan(self, keywords: List[str], limit: int = 10) -> List[SearchResult]:
        """Perform a keyword/regex scan on documents."""
        if not self._documents:
            return []
            
        results = []
        import re
        patterns = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in keywords]
        
        for doc in self._documents:
            lower_text = doc.text.lower()
            match_count = 0
            for pattern in patterns:
                if pattern.search(doc.text):
                    match_count += 1
            
            if match_count > 0:
                results.append(SearchResult(
                    text=doc.text,
                    metadata=doc.metadata,
                    score=min(1.0, 0.5 + (match_count * 0.1))
                ))
            
            if len(results) >= limit:
                break
                
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def expand_neighbors(self, base_results: List[SearchResult], limit_per_hit: int = 3) -> List[SearchResult]:
        """Expand retrieval to include neighboring pages/sections."""
        expanded_results = list(base_results)
        seen_ids = {f"{r.metadata.get('doc_id')}_{r.metadata.get('page')}_{r.metadata.get('chunk_index')}" for r in base_results}
        
        for res in base_results:
            doc_id = res.metadata.get("doc_id")
            page = res.metadata.get("page")
            section_id = res.metadata.get("section_id")
            topic_tags = res.metadata.get("topic_tags", [])
            
            # 1. Same page (±1)
            if page:
                neighbor_pages = self.search_by_metadata({"doc_id": doc_id, "page": page}, limit=5)
                # Also try page-1 if page > 1
                if page > 1:
                    neighbor_pages.extend(self.search_by_metadata({"doc_id": doc_id, "page": page - 1}, limit=5))
                neighbor_pages.extend(self.search_by_metadata({"doc_id": doc_id, "page": page + 1}, limit=5))
                
                for nr in neighbor_pages:
                    nr_id = f"{nr.metadata.get('doc_id')}_{nr.metadata.get('page')}_{nr.metadata.get('chunk_index')}"
                    if nr_id not in seen_ids:
                        nr.score = 0.8 # Neighbors have slightly lower score
                        expanded_results.append(nr)
                        seen_ids.add(nr_id)

            # 2. Section range neighbours (e.g. 7201..7209 if base is 7207)
            if section_id:
                # Find range
                section_start = (section_id // 10) * 10
                section_end = section_start + 9
                neighbor_sections = self.search_by_metadata({"doc_id": doc_id, "section_id": (section_start, section_end)}, limit=10)
                
                for nr in neighbor_sections:
                    nr_id = f"{nr.metadata.get('doc_id')}_{nr.metadata.get('page')}_{nr.metadata.get('chunk_index')}"
                    if nr_id not in seen_ids:
                        nr.score = 0.85
                        expanded_results.append(nr)
                        seen_ids.add(nr_id)
            
            # 3. Same topic tag (e.g. "regionals")
            for tag in topic_tags:
                topic_results = self.search_by_metadata({"topic_tags": tag}, limit=5)
                for tr in topic_results:
                    tr_id = f"{tr.metadata.get('doc_id')}_{tr.metadata.get('page')}_{tr.metadata.get('chunk_index')}"
                    if tr_id not in seen_ids:
                        tr.score = 0.75
                        expanded_results.append(tr)
                        seen_ids.add(tr_id)
                        
        return expanded_results
    
    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Delete all chunks for a document.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            Deletion summary
        """
        # Find indices to delete
        indices_to_delete = [i for i, doc in enumerate(self._documents) 
                           if doc.metadata.get("doc_id") == doc_id]
        
        if not indices_to_delete:
            return {"status": "not_found", "message": f"No document with ID {doc_id}"}
        
        # Remove from documents list
        indices_to_keep = [i for i in range(len(self._documents)) 
                         if i not in indices_to_delete]
        
        self._documents = [self._documents[i] for i in indices_to_keep]
        
        # Update embeddings matrix
        if indices_to_keep and self._embeddings is not None:
            self._embeddings = self._embeddings[indices_to_keep]
        else:
            self._embeddings = None
        
        # Persist changes
        self._save()
        
        return {
            "status": "success",
            "doc_id": doc_id,
            "chunks_deleted": len(indices_to_delete)
        }
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents."""
        # Group by document
        docs = {}
        for doc in self._documents:
            doc_id = doc.metadata.get("doc_id")
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "filename": doc.metadata.get("filename", "Unknown"),
                    "chunk_count": 0
                }
            docs[doc_id]["chunk_count"] += 1
        
        return list(docs.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        docs = self.list_documents()
        return {
            "total_chunks": len(self._documents),
            "total_documents": len(docs),
            "documents": docs
        }
