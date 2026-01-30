# TCBot - Local RAG Text Bot

This is a Retrieval Augmented Generation (RAG) bot built with Python, FastAPI, Redis, SQLite, ChromaDB, and Ollama.

## Features
- Upload PDF documents.
- Automatic chunking and embedding (using Ollama's `nomic-embed-text` or similar).
- Store vectors in ChromaDB (persistent).
- Query the bot using Llama 3 (via Ollama).
- Production-ready structure with Docker support.

## Prerequisites
- Docker & Docker Compose
- [Ollama](https://ollama.com/) installed and running locally.
- Pull the necessary models in Ollama:
  ```bash
  ollama pull llama3
  ollama pull nomic-embed-text
  ```

## Setup & Run

### 1. Using Docker (Recommended)
This starts the API and Redis.

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### 2. Local Development
Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the server:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- **Swagger UI**: `http://localhost:8000/docs`
- `POST /api/v1/upload`: Upload a PDF file.
- `POST /api/v1/chat?query=...`: Chat with your documents.
- `GET /api/v1/documents`: List uploaded documents.

## Technology Stack
- **Framework**: FastAPI
- **DB (Metadata)**: SQLite
- **Vector DB**: ChromaDB
- **LLM/Embedding**: Ollama (Llama 3 / Nomic)
- **Cache/Broker**: Redis (Prepared for scalability)
