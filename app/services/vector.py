import os
from app.config import settings

# Cache for vector store
_vector_store_cache = None

def get_vector_store():
    """
    Get the appropriate vector store based on environment.
    Uses ChromaDB locally, serverless version on Vercel.
    """
    global _vector_store_cache
    
    if _vector_store_cache is not None:
        return _vector_store_cache
    
    # Use serverless version on Vercel (lighter weight)
    if os.environ.get("VERCEL"):
        from app.services.vector_serverless import ServerlessVectorStore
        _vector_store_cache = ServerlessVectorStore(api_key=settings.OPENAI_API_KEY)
        print("✅ Using ServerlessVectorStore for Vercel deployment")
        return _vector_store_cache
    
    # Use ChromaDB locally - import dependencies here to avoid loading on Vercel
    from langchain_chroma import Chroma
    from app.services.utils import get_embeddings
    
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
    Note: This only works locally, not on Vercel.
    """
    if os.environ.get("VERCEL"):
        print("⚠️ Cannot add documents on Vercel - read-only deployment")
        return False
    
    store = get_vector_store()
    
    # ChromaDB's add_documents handles embedding internally
    store.add_documents(chunks)
    
    print(f"✅ Added {len(chunks)} chunks to ChromaDB.")
    return True
