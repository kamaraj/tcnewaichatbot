import os
import time
import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from app.services.vector import add_documents_to_vector_store
from app.services.utils import get_embeddings
from app.models.db import Document
from sqlalchemy.orm import Session

def clean_text(text: str) -> str:
    """Clean and normalize text for better chunking"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page headers/footers patterns (common in rulebooks)
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
    return text.strip()

def process_document(file_path: str, doc_id: int, db: Session):
    start_total = time.time()
    
    try:
        # Update status to processing
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.processing_status = "processing"
            db.commit()
        
        # 1. Load PDF
        print(f"📄 Loading PDF: {file_path}")
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        num_pages = len(docs)
        print(f"📖 Loaded {num_pages} pages")
        
        # Clean the documents
        for d in docs:
            d.page_content = clean_text(d.page_content)
        
        # 2. SEMANTIC CHUNKING - keeps related content together
        start_chunking = time.time()
        
        print(f"🔬 Starting semantic chunking...")
        embeddings = get_embeddings()
        
        semantic_chunker = SemanticChunker(
            embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=85,
        )
        
        # Combine all pages for semantic analysis
        full_text = "\n\n".join([d.page_content for d in docs])
        chunks = semantic_chunker.create_documents([full_text])
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata = {
                "source": file_path,
                "filename": os.path.basename(file_path),
                "chunk_index": i,
                "chunking_method": "semantic"
            }
        
        print(f"✅ Semantic chunking complete: {len(chunks)} chunks created")
        
        chunking_time = (time.time() - start_chunking) * 1000
        
        # Add document ID to all chunks
        for chunk in chunks:
            chunk.metadata["source_doc_id"] = doc_id
            chunk.metadata["filename"] = os.path.basename(file_path)

        # 3. Embed and Store in ChromaDB
        print(f"💾 Storing {len(chunks)} chunks in ChromaDB...")
        start_embedding = time.time()
        add_documents_to_vector_store(chunks)
        embedding_time = (time.time() - start_embedding) * 1000
        
        total_time = (time.time() - start_total) * 1000
        
        # 4. Update DB with metrics
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.processed = True
            doc.processing_status = "completed"
            doc.num_chunks = len(chunks)
            doc.num_pages = num_pages
            doc.chunking_time_ms = round(chunking_time, 2)
            doc.embedding_time_ms = round(embedding_time, 2)
            doc.total_processing_time_ms = round(total_time, 2)
            db.commit()
        
        print(f"✅ Document processing complete!")
        print(f"   Pages: {num_pages}, Chunks: {len(chunks)}")
        print(f"   Chunking: {chunking_time:.0f}ms, Embedding: {embedding_time:.0f}ms, Total: {total_time:.0f}ms")
            
        return {
            "status": "success", 
            "chunks_processed": len(chunks),
            "pages": num_pages,
            "chunking_method": "semantic",
            "metrics": {
                "chunking_time_ms": round(chunking_time, 2),
                "embedding_time_ms": round(embedding_time, 2),
                "total_time_ms": round(total_time, 2)
            }
        }
        
    except Exception as e:
        print(f"❌ Error processing document {doc_id}: {e}")
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.error_message = str(e)
            db.commit()
        return {"status": "error", "message": str(e)}
