"""
TCA AI Chatbot - Main Application Entry Point.
A lightweight RAG chatbot for PDF document Q&A.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from .api import router
from .config import settings

# Create FastAPI app
app = FastAPI(
    title="TCA AI Chatbot",
    description="A lightweight RAG-based chatbot for PDF document question answering",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Serve the main chat interface."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "TCA AI Chatbot API", "docs": "/docs"}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("=" * 50)
    print("TCA AI Chatbot Starting...")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Embedding Model: {settings.embedding_model}")
    print(f"Upload Directory: {settings.upload_dir}")
    print(f"Data Directory: {settings.chroma_persist_dir}")
    print("=" * 50)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
