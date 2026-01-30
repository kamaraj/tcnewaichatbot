"""
Run script for TCA AI Chatbot.
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("TCA AI Chatbot - RAG-based PDF Question Answering")
    print("=" * 60)
    print(f"Server: http://localhost:{settings.port}")
    print(f"API Docs: http://localhost:{settings.port}/docs")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Embedding Model: {settings.embedding_model}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=["app"]
    )
