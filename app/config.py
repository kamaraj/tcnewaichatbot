"""
Configuration settings for the RAG Chatbot.
Supports multiple LLM providers: Ollama, Claude, Qwen
"""

from pydantic_settings import BaseSettings
from typing import Literal
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider
    llm_provider: Literal["ollama", "claude", "qwen"] = "ollama"
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "tinyllama"
    
    # Claude Configuration
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    # Qwen Configuration
    qwen_api_key: str = ""
    qwen_model: str = "qwen-turbo"
    
    # Embedding Model (Ollama-based - no PyTorch/ONNX needed)
    embedding_model: str = "nomic-embed-text"
    
    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "pdf_documents"
    
    # Upload Configuration
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    
    # Chunking Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Retrieval Configuration
    top_k_results: int = 5
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)
