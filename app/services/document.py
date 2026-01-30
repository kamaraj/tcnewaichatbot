import os
import time
import re
# Imports made local to process_document to allow core app to run without these heavy dependencies on Vercel
# from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_experimental.text_splitter import SemanticChunker
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
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        num_pages = len(docs)
        
        # Clean the documents
        for d in docs:
            d.page_content = clean_text(d.page_content)
        
        # 2. SEMANTIC CHUNKING - keeps related content together
        start_chunking = time.time()
        
        try:
            # Try semantic chunking first (best for rulebooks)
            # Use a slightly lower threshold to be more aggressive with splitting, saving time 
            embeddings = get_embeddings()
            
            # Simple check: If document is too large (>20 pages), skip semantic to avoid timeout
            if num_pages > 20:
                raise Exception("Document too large for semantic chunking, using recursive")

            semantic_chunker = SemanticChunker(
                embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=85, 
            )
            
            # Combine all pages for semantic analysis
            full_text = "\n\n".join([d.page_content for d in docs])
            chunks = semantic_chunker.create_documents([full_text])
            
            # Add metadata back to chunks
            for i, chunk in enumerate(chunks):
                chunk.metadata = {
                    "source": file_path,
                    "filename": os.path.basename(file_path),
                    "chunk_index": i,
                    "chunking_method": "semantic"
                }
            
            print(f"✅ Semantic chunking: {len(chunks)} chunks created")
            
        except Exception as e:
            print(f"⚠️ Semantic chunking skipped: {e}")
            # Fallback to recursive chunking with section-aware splitting
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,  # Smaller chunks for TinyLlama
                chunk_overlap=200,
                separators=[
                    "\n\n",  # Double newlines (paragraphs)
                    "\nSection ",  # Section headers
                    "\nARTICLE ",  # Article headers
                    "\nRule ",  # Rule headers
                    "\n\d+\.",  # Numbered items
                    "\n",  # Single newlines
                    ". ",  # Sentences
                    " ",  # Words
                ],
                add_start_index=True
            )
            chunks = text_splitter.split_documents(docs)
            
            for chunk in chunks:
                chunk.metadata["chunking_method"] = "recursive"
        
        chunking_time = (time.time() - start_chunking) * 1000
        
        # Add document ID to all chunks
        for chunk in chunks:
            chunk.metadata["source_doc_id"] = doc_id
            chunk.metadata["filename"] = os.path.basename(file_path)

        # 3. Embed and Store
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
            
        return {
            "status": "success", 
            "chunks_processed": len(chunks),
            "pages": num_pages,
            "chunking_method": chunks[0].metadata.get("chunking_method", "unknown") if chunks else "none",
            "metrics": {
                "chunking_time_ms": round(chunking_time, 2),
                "embedding_time_ms": round(embedding_time, 2),
                "total_time_ms": round(total_time, 2)
            }
        }
        
    except Exception as e:
        print(f"Error processing document {doc_id}: {e}")
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.error_message = str(e)
            db.commit()
        return {"status": "error", "message": str(e)}
