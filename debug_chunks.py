import sys
import os
import pickle
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from app.services.vector_store import VectorStore

def check_chunks():
    # Force load from disk
    persist_dir = Path("./chroma_db")
    data_file = persist_dir / "vector_store.pkl"
    
    if not data_file.exists():
        print("No vector store found.")
        return

    with open(data_file, 'rb') as f:
        data = pickle.load(f)
        docs = data.get('documents', [])
        
    print(f"Total docs: {len(docs)}")
    
    count = 0
    for doc in docs:
        if doc.metadata.get('page') == 1:
            count += 1
            print(f"\n[{count}] Chunk ID: {doc.chunk_id}")
            print(f"Metadata: {doc.metadata}")
            print(f"Text len: {len(doc.text)}")
            print("-" * 20)
            print(doc.text)
            print("-" * 20)

if __name__ == "__main__":
    check_chunks()
