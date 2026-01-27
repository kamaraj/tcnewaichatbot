"""
API Routes for the RAG Chatbot.
"""

import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from ..services import PDFProcessor, VectorStore, RAGService
from ..llm import get_llm_provider, check_llm_status
from ..config import settings

router = APIRouter()

# Initialize services
pdf_processor = PDFProcessor()
vector_store = VectorStore()
rag_service = RAGService()


# Request/Response Models
class ChatRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    query: str


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class UploadResponse(BaseModel):
    status: str
    doc_id: str
    filename: str
    chunks_indexed: int
    message: str


class HealthResponse(BaseModel):
    status: str
    llm: dict
    vector_store: dict


# Health Check
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health of all services."""
    llm_status = await check_llm_status()
    vs_stats = vector_store.get_stats()
    
    return HealthResponse(
        status="healthy" if llm_status["status"] == "healthy" else "degraded",
        llm=llm_status,
        vector_store={
            "status": "healthy",
            "total_documents": vs_stats["total_documents"],
            "total_chunks": vs_stats["total_chunks"]
        }
    )


# Document Upload
@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a PDF document."""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size
    content = await file.read()
    max_size = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum of {settings.max_file_size_mb}MB"
        )
    
    try:
        # Save the file
        file_path = pdf_processor.save_uploaded_file(content, file.filename)
        
        # Process the PDF
        processed_doc = pdf_processor.process_pdf(file_path, file.filename)
        
        # Index in vector store
        result = vector_store.add_document(processed_doc)
        
        return UploadResponse(
            status="success",
            doc_id=result["doc_id"],
            filename=file.filename,
            chunks_indexed=result["chunks_indexed"],
            message=f"Successfully indexed {result['chunks_indexed']} chunks from {file.filename}"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


# Chat Endpoint
@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with your documents."""
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if request.stream:
        # Return streaming response
        async def generate():
            async for chunk in rag_service.query_stream(
                question=request.question,
                filter_doc_id=request.doc_id
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        # Return complete response
        try:
            response = await rag_service.query(
                question=request.question,
                filter_doc_id=request.doc_id
            )
            
            return ChatResponse(
                answer=response.answer,
                sources=response.sources,
                query=response.query
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


# Document Management
@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all indexed documents."""
    docs = vector_store.list_documents()
    return [DocumentInfo(**doc) for doc in docs]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the index."""
    result = vector_store.delete_document(doc_id)
    
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


@router.get("/documents/{doc_id}/search")
async def search_document(
    doc_id: str,
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results")
):
    """Search within a specific document."""
    results = vector_store.search(query=query, top_k=top_k, filter_doc_id=doc_id)
    
    return {
        "query": query,
        "results": [
            {
                "text": r.text,
                "page": r.metadata.get("page"),
                "score": round(r.score, 3)
            }
            for r in results
        ]
    }


# LLM Info
@router.get("/llm/models")
async def list_models():
    """List available LLM models (for Ollama)."""
    try:
        provider = get_llm_provider()
        if hasattr(provider, 'list_models'):
            models = await provider.list_models()
            return {"models": models}
        return {"models": [], "message": "Model listing not supported for this provider"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
