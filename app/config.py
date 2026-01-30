import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "TCBot RAG"
    API_V1_STR: str = "/api/v1"
    
    # Database (SQLite)
    # Use /tmp on Vercel for writable filesystem
    SQLITE_URL: str = "sqlite:///./data/sql_app.db"
    if os.environ.get("VERCEL"):
        SQLITE_URL = "sqlite:////tmp/sql_app.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector DB (FAISS/Chroma)
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    FAISS_INDEX_PATH: str = "./data/faiss_index"
    
    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # File Upload
    UPLOAD_DIR: str = "./data/uploads"

    # OpenAI
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "openai" # ollama or openai
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_FALLBACK_MODELS: list = ["gpt-4-turbo", "gpt-3.5-turbo"]
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure directories exist (Skip on Vercel as it is read-only)
if not os.environ.get("VERCEL"):
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
