import os
from app.config import settings
from app.services.utils import get_embeddings

# ChromaDB-based vector store
_vector_store_cache = None

def get_vector_store():
    """
    ChromaDB-based vector store for robust document retrieval.
    Caches the store instance to avoid reloading.
    """
    global _vector_store_cache
    
    if _vector_store_cache is not None:
        return _vector_store_cache
    
    from langchain_chroma import Chroma
    
    persist_directory = settings.CHROMA_PERSIST_DIRECTORY
    
    # Ensure directory exists
    os.makedirs(persist_directory, exist_ok=True)
    
    embeddings = get_embeddings()
    
    # Check if ChromaDB already has data
    if os.path.exists(os.path.join(persist_directory, "chroma.sqlite3")):
        print(f"📦 Loading existing ChromaDB from {persist_directory}...")
        _vector_store_cache = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name="ihsa_rulebook"
        )
        print(f"✅ ChromaDB loaded successfully.")
    else:
        print(f"🆕 Creating new ChromaDB at {persist_directory}...")
        _vector_store_cache = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name="ihsa_rulebook"
        )
        print(f"✅ ChromaDB created.")
    
    return _vector_store_cache

def add_documents_to_vector_store(chunks):
    """
    Add document chunks to ChromaDB vector store.
    """
    store = get_vector_store()
    
    # ChromaDB's add_documents handles embedding internally
    store.add_documents(chunks)
    
    print(f"✅ Added {len(chunks)} chunks to ChromaDB.")
    return True
