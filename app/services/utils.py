from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings

def get_llm(model_name: str = None):
    if settings.LLM_PROVIDER == "openai":
        return ChatOpenAI(
            model=model_name or settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=0.1
    )

def get_embeddings():
    if settings.LLM_PROVIDER == "openai":
        # Using a standard OpenAI embedding model
        # You might want to make this configurable in settings as well
        return OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.EMBEDDING_MODEL 
    )
