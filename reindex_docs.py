import os
import shutil
import sys
from sqlalchemy.orm import Session

# Add the current directory to sys.path so we can import app modules
sys.path.append(os.getcwd())

from app.models.db import SessionLocal, Document, init_db
from app.services.document import process_document
from app.config import settings

def reset_and_reindex():
    print("🚀 Starting Re-indexing Process...")
    
    # 1. Clear Vector Store
    if os.path.exists(settings.CHROMA_PERSIST_DIRECTORY):
        print(f"🗑️  Removing existing vector store at {settings.CHROMA_PERSIST_DIRECTORY}...")
        try:
            shutil.rmtree(settings.CHROMA_PERSIST_DIRECTORY)
            print("✅ Vector store cleared.")
        except Exception as e:
            print(f"❌ Error removing vector store: {e}")
            return
    else:
        print("ℹ️  No existing vector store found.")

    # 2. Reset Database Records
    db: Session = SessionLocal()
    try:
        docs = db.query(Document).all()
        print(f"📄 Found {len(docs)} documents in database.")
        
        if not docs:
            print("⚠️  No documents to re-index.")
            return

        for doc in docs:
            print(f"🔄 Resetting status for: {doc.filename}")
            doc.processed = False
            doc.processing_status = "pending"
            doc.num_chunks = 0
            doc.num_pages = 0
            doc.error_message = None
            # Reset metrics
            doc.chunking_time_ms = 0
            doc.embedding_time_ms = 0
            doc.total_processing_time_ms = 0
        
        db.commit()
        print("✅ Database records reset.")
        
        # 3. Re-process Documents
        print("\n⚙️  Re-processing documents with new embeddings...")
        
        for i, doc in enumerate(docs):
            print(f"[{i+1}/{len(docs)}] Processing {doc.filename}...")
            
            # Check if file exists
            if not os.path.exists(doc.filepath):
                print(f"⚠️  File not found at {doc.filepath}, skipping.")
                doc.processing_status = "failed"
                doc.error_message = "File not found during re-index"
                db.commit()
                continue
                
            result = process_document(doc.filepath, doc.id, db)
            
            if result.get("status") == "success":
                print(f"   ✅ Success: {result['metrics']['total_time_ms']}ms")
            else:
                print(f"   ❌ Failed: {result.get('message')}")
                
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        db.close()
        print("\n✨ Re-indexing complete!")

if __name__ == "__main__":
    # Ensure directories exist (in case we deleted them)
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    reset_and_reindex()
