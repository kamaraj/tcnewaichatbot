import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "IHSA Rulebook AI"
    API_V1_STR: str = "/api/v1"
    
    # Database (SQLite)
    # Use /tmp on Vercel for writable filesystem
    SQLITE_URL: str = "sqlite:///./data/sql_app.db"
    
    # Vector DB (ChromaDB)
    # On Vercel, the filesystem is read-only except /tmp
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    
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

# Create settings instance
settings = Settings()

# Handle Vercel environment
if os.environ.get("VERCEL"):
    # Use /tmp for writable storage on Vercel
    settings.SQLITE_URL = "sqlite:////tmp/sql_app.db"
    # ChromaDB data is bundled with the deployment (read-only)
    # No need to change the path as it's read from the deployed files

# Ensure directories exist (Skip on Vercel as most paths are read-only)
if not os.environ.get("VERCEL"):
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

