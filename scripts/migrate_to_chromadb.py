#!/usr/bin/env python3
"""
Script to migrate existing vector_index.json data to ChromaDB
"""
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.utils import get_embeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document

def migrate_to_chromadb():
    json_path = os.path.join(os.getcwd(), "data", "vector_index.json")
    
    if not os.path.exists(json_path):
        print(f"❌ vector_index.json not found at {json_path}")
        return False
    
    print(f"📦 Loading data from {json_path}...")
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    texts = data.get('texts', [])
    metadatas = data.get('metadatas', [])
    
    print(f"Found {len(texts)} documents to migrate")
    
    if len(texts) == 0:
        print("No documents to migrate")
        return False
    
    # Create Document objects
    documents = []
    for i, (text, metadata) in enumerate(zip(texts, metadatas)):
        documents.append(Document(
            page_content=text,
            metadata=metadata
        ))
    
    print(f"📝 Creating ChromaDB with {len(documents)} documents...")
    
    # Initialize ChromaDB
    persist_directory = settings.CHROMA_PERSIST_DIRECTORY
    os.makedirs(persist_directory, exist_ok=True)
    
    embeddings = get_embeddings()
    
    # Create new ChromaDB collection
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name="ihsa_rulebook"
    )
    
    print(f"✅ Migration complete! ChromaDB created at {persist_directory}")
    print(f"📊 Total documents: {len(documents)}")
    
    return True

if __name__ == "__main__":
    migrate_to_chromadb()
