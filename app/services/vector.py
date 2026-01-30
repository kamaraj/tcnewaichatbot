import os
import json
import numpy as np
from app.config import settings
from app.services.utils import get_embeddings

# Define index path - be robust about finding it
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(os.getcwd(), "data", "vector_index.json")
if not os.path.exists(INDEX_PATH):
    # Try relative to the script
    INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "vector_index.json")

_vector_store_cache = None

def get_vector_store():
    """
    Simple Numpy-based vector store for Vercel compatibility.
    No heavy binary dependencies like FAISS or Chroma.
    Caches the store instance to avoid reloading large JSON files.
    """
    global _vector_store_cache
    
    if _vector_store_cache is not None:
        return _vector_store_cache
        
    class SimpleVectorStore:
        def __init__(self, embeddings_model):
            self.embeddings_model = embeddings_model
            self.texts = []
            self.metadatas = []
            self.vectors = []
            self._load()

        def _load(self):
            if os.path.exists(INDEX_PATH):
                try:
                    print(f"📦 Loading vector index from {INDEX_PATH}...")
                    with open(INDEX_PATH, 'r') as f:
                        data = json.load(f)
                        self.texts = data.get('texts', [])
                        self.metadatas = data.get('metadatas', [])
                        self.vectors = np.array(data.get('vectors', []))
                    print(f"✅ Loaded {len(self.texts)} vectors.")
                except Exception as e:
                    print(f"❌ Error loading vector index: {e}")
            else:
                print(f"⚠️ Vector index file not found at {INDEX_PATH}")

        def save(self):
            os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
            with open(INDEX_PATH, 'w') as f:
                json.dump({
                    'texts': self.texts,
                    'metadatas': self.metadatas,
                    'vectors': self.vectors.tolist() if isinstance(self.vectors, np.ndarray) else self.vectors
                }, f)

        def add_documents(self, chunks):
            new_texts = [c.page_content for c in chunks]
            new_metadatas = [c.metadata for c in chunks]
            
            # Get embeddings for new texts
            new_vectors = self.embeddings_model.embed_documents(new_texts)
            
            self.texts.extend(new_texts)
            self.metadatas.extend(new_metadatas)
            
            if len(self.vectors) == 0:
                self.vectors = np.array(new_vectors)
            else:
                self.vectors = np.vstack([self.vectors, np.array(new_vectors)])
            
            self.save()

        def similarity_search(self, query, k=5):
            if len(self.vectors) == 0:
                return []
            
            query_vector = np.array(self.embeddings_model.embed_query(query))
            
            # Cosine similarity
            similarities = np.dot(self.vectors, query_vector)
            indices = np.argsort(similarities)[-k:][::-1]
            
            from langchain.docstore.document import Document
            results = []
            for i in indices:
                results.append(Document(
                    page_content=self.texts[i],
                    metadata=self.metadatas[i]
                ))
            return results

        def as_retriever(self, **kwargs):
            class SimpleRetriever:
                def __init__(self, store, k=10):
                    self.store = store
                    self.k = k
                def get_relevant_documents(self, query):
                    return self.store.similarity_search(query, k=self.k)
            return SimpleRetriever(self, k=kwargs.get("search_kwargs", {}).get("k", 10))

    _vector_store_cache = SimpleVectorStore(get_embeddings())
    return _vector_store_cache

def add_documents_to_vector_store(chunks):
    store = get_vector_store()
    store.add_documents(chunks)
    return True
