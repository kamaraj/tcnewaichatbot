from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.db import get_db, Document, QueryLog
from app.config import settings
from pydantic import BaseModel
from typing import Optional
import shutil
import os
import uuid
import time

# Conditional import based on environment
if os.environ.get("VERCEL"):
    from app.services.chat_serverless import generate_answer_serverless as generate_answer
else:
    from app.services.chat import generate_answer
    from app.services.document import process_document

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Document upload is not supported on Vercel (read-only filesystem)
    if os.environ.get("VERCEL"):
        raise HTTPException(
            status_code=400, 
            detail="Document upload is not supported on Vercel. Please use the local development environment to upload documents."
        )
    
    start_time = time.time()
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save file locally
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    # Get file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    upload_time = (time.time() - start_time) * 1000
        
    # Create DB record with metrics
    db_doc = Document(
        filename=file.filename, 
        filepath=file_path,
        file_size_bytes=file_size,
        upload_time_ms=round(upload_time, 2),
        processing_status="pending"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Trigger background processing
    background_tasks.add_task(process_document, file_path, db_doc.id, db)
    
    return {
        "message": "File uploaded successfully, processing started", 
        "document_id": db_doc.id,
        "file_size_bytes": file_size,
        "upload_time_ms": round(upload_time, 2)
    }

@router.post("/chat")
async def chat(query: str = None, body: ChatRequest = None, db: Session = Depends(get_db)):
    # Support both query param and body
    query_text = query or (body.query if body else None)
    
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY is not configured in environment variables. Please add it to Vercel settings."
        )
    
    try:
        result = await generate_answer(query_text, db)
        return result
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.upload_date.desc()).all()
    return [{
        "id": doc.id,
        "filename": doc.filename,
        "file_size_bytes": doc.file_size_bytes,
        "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
        "processed": doc.processed,
        "processing_status": doc.processing_status,
        "num_chunks": doc.num_chunks,
        "num_pages": doc.num_pages,
        "metrics": {
            "upload_time_ms": doc.upload_time_ms,
            "chunking_time_ms": doc.chunking_time_ms,
            "embedding_time_ms": doc.embedding_time_ms,
            "total_processing_time_ms": doc.total_processing_time_ms
        },
        "error_message": doc.error_message
    } for doc in docs]

@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get comprehensive dashboard statistics"""
    
    # Document stats
    total_docs = db.query(Document).count()
    processed_docs = db.query(Document).filter(Document.processed == True).count()
    pending_docs = db.query(Document).filter(Document.processing_status == "pending").count()
    failed_docs = db.query(Document).filter(Document.processing_status == "failed").count()
    
    # Chunk stats
    total_chunks = db.query(func.sum(Document.num_chunks)).scalar() or 0
    total_pages = db.query(func.sum(Document.num_pages)).scalar() or 0
    
    # Storage stats
    total_size_bytes = db.query(func.sum(Document.file_size_bytes)).scalar() or 0
    
    # Processing time stats
    avg_processing_time = db.query(func.avg(Document.total_processing_time_ms)).filter(
        Document.processed == True
    ).scalar() or 0
    avg_chunking_time = db.query(func.avg(Document.chunking_time_ms)).filter(
        Document.processed == True
    ).scalar() or 0
    avg_embedding_time = db.query(func.avg(Document.embedding_time_ms)).filter(
        Document.processed == True
    ).scalar() or 0
    
    # Query stats
    total_queries = db.query(QueryLog).count()
    avg_query_time = db.query(func.avg(QueryLog.total_time_ms)).scalar() or 0
    avg_retrieval_time = db.query(func.avg(QueryLog.retrieval_time_ms)).scalar() or 0
    avg_generation_time = db.query(func.avg(QueryLog.generation_time_ms)).scalar() or 0
    
    # Recent queries
    recent_queries = db.query(QueryLog).order_by(QueryLog.query_time.desc()).limit(10).all()
    
    return {
        "documents": {
            "total": total_docs,
            "processed": processed_docs,
            "pending": pending_docs,
            "failed": failed_docs,
            "success_rate": round((processed_docs / total_docs * 100) if total_docs > 0 else 0, 1)
        },
        "content": {
            "total_chunks": total_chunks,
            "total_pages": total_pages,
            "avg_chunks_per_doc": round(total_chunks / processed_docs if processed_docs > 0 else 0, 1)
        },
        "storage": {
            "total_bytes": total_size_bytes,
            "total_mb": round(total_size_bytes / (1024 * 1024), 2) if total_size_bytes else 0
        },
        "processing_performance": {
            "avg_total_time_ms": round(avg_processing_time, 2),
            "avg_chunking_time_ms": round(avg_chunking_time, 2),
            "avg_embedding_time_ms": round(avg_embedding_time, 2)
        },
        "query_performance": {
            "total_queries": total_queries,
            "avg_total_time_ms": round(avg_query_time, 2),
            "avg_retrieval_time_ms": round(avg_retrieval_time, 2),
            "avg_generation_time_ms": round(avg_generation_time, 2)
        },
        "recent_queries": [{
            "id": q.id,
            "query": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
            "time": q.query_time.isoformat() if q.query_time else None,
            "total_time_ms": q.total_time_ms
        } for q in recent_queries]
    }

@router.get("/documents/{doc_id}")
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_size_bytes": doc.file_size_bytes,
        "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
        "processed": doc.processed,
        "processing_status": doc.processing_status,
        "num_chunks": doc.num_chunks,
        "num_pages": doc.num_pages,
        "metrics": {
            "upload_time_ms": doc.upload_time_ms,
            "chunking_time_ms": doc.chunking_time_ms,
            "embedding_time_ms": doc.embedding_time_ms,
            "total_processing_time_ms": doc.total_processing_time_ms
        },
        "error_message": doc.error_message
    }
