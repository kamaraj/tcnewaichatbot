# from langchain_chroma import Chroma
from app.config import settings
from app.services.utils import get_embeddings
# import chromadb

# Initialize the persistent client globally or per request if needed
# LangChain's Chroma wrapper handles persistence well.

def get_vector_store():
    # Only creating the client once is generally better, but for simplicity here we re-init.
    # In a high-load prod app, you might cache this.
    return Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
        embedding_function=get_embeddings(),
        collection_name="tcbot_documents"
    )

def add_documents_to_vector_store(chunks):
    vector_store = get_vector_store()
    vector_store.add_documents(documents=chunks)
    # Chroma 0.4+ persists automatically usually, but explicitly calling persist() was deprecated/removed in newer langchain versions
    # We rely on auto-persistence config of ChromaDB
    return True
