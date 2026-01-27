# TCA AI Chatbot - RAG-based PDF Question Answering

A lightweight chatbot that answers questions from your PDF documents using:
- **TinyLlama** (via Ollama) - Local LLM inference
- **ChromaDB** - Vector database for document embeddings
- **Sentence Transformers** - Local embedding generation
- **FastAPI** - High-performance Python backend
- **Bootstrap 5** - Clean, responsive UI

![TCA AI Chatbot](https://img.shields.io/badge/RAG-Chatbot-6366f1?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## Features

✅ **PDF Document Upload** - Upload and index PDF files  
✅ **Semantic Search** - Find relevant information using embeddings  
✅ **RAG Pipeline** - Retrieval-Augmented Generation for accurate answers  
✅ **Source Citations** - See which pages the answer came from  
✅ **Streaming Responses** - Real-time answer generation  
✅ **Dark Theme UI** - Modern, clean interface  
✅ **Switchable LLM** - Easy to change from TinyLlama to Claude/Qwen  

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Upload PDF    │────▶│  Extract Text    │────▶│   Chunk Text    │
└─────────────────┘     │   (PyMuPDF)      │     │  (500 tokens)   │
                        └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              ▼
                        │   Store Vectors   │◀────  Embed Chunks
                        │   (ChromaDB)      │     (MiniLM-L6-v2)
                        └────────┬─────────┘
                                 │
┌─────────────────┐              ▼
│  User Question  │────▶ Retrieve Top-K Chunks
└─────────────────┘              │
                                 ▼
                        ┌──────────────────┐
                        │  Build RAG Prompt │
                        │  + Call TinyLlama │
                        │    (via Ollama)   │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Return Answer   │
                        │  + Citations     │
                        └──────────────────┘
```

## Prerequisites

1. **Python 3.10+** installed
2. **Ollama** installed and running with TinyLlama

### Install Ollama

```bash
# Windows - Download from https://ollama.ai/download

# After installation, pull TinyLlama
ollama pull tinyllama
```

## Quick Start

### 1. Create Virtual Environment

```bash
cd C:\kamaraj\prototype\TCAIChatbot
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Ollama (in a separate terminal)

```bash
ollama serve
```

### 4. Run the Application

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open the Application

Navigate to: **http://localhost:8000**

## Usage

1. **Upload a PDF** - Drag & drop or click to upload
2. **Wait for indexing** - The document will be chunked and embedded
3. **Ask questions** - Type your question in the chat
4. **View sources** - See which pages the answer came from

## Project Structure

```
TCAIChatbot/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration settings
│   ├── main.py             # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # API endpoints
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py         # Base LLM provider
│   │   ├── ollama_provider.py  # Ollama/TinyLlama
│   │   ├── claude_provider.py  # Claude (future)
│   │   └── factory.py      # Provider factory
│   └── services/
│       ├── __init__.py
│       ├── pdf_processor.py    # PDF extraction & chunking
│       ├── vector_store.py     # ChromaDB operations
│       └── rag_service.py      # RAG orchestration
├── static/
│   ├── index.html          # Main UI
│   ├── css/
│   │   └── styles.css      # Custom styles
│   └── js/
│       └── app.js          # Frontend logic
├── uploads/                # Uploaded PDFs
├── chroma_db/              # Vector database
├── requirements.txt
├── .env                    # Configuration
├── run.py                  # Run script
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/upload` | POST | Upload PDF document |
| `/api/chat` | POST | Chat with documents |
| `/api/documents` | GET | List indexed documents |
| `/api/documents/{id}` | DELETE | Delete a document |
| `/api/llm/models` | GET | List available models |

## Switching LLM Providers

### Use a Different Ollama Model

Edit `.env`:
```env
OLLAMA_MODEL=mistral
# or
OLLAMA_MODEL=phi
# or
OLLAMA_MODEL=qwen:7b
```

### Switch to Claude

Edit `.env`:
```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your-api-key-here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | ollama | LLM provider (ollama, claude, qwen) |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama API URL |
| `OLLAMA_MODEL` | tinyllama | Model to use |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence transformer model |
| `CHUNK_SIZE` | 500 | Text chunk size in characters |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks |
| `TOP_K_RESULTS` | 5 | Number of chunks to retrieve |
| `MAX_FILE_SIZE_MB` | 50 | Maximum upload file size |

## Troubleshooting

### Ollama not running
```bash
# Start Ollama
ollama serve

# Check if TinyLlama is installed
ollama list

# Pull TinyLlama if missing
ollama pull tinyllama
```

### Slow responses
- TinyLlama is optimized for speed, but complex questions take longer
- Consider using a GPU-enabled machine for faster inference
- Reduce `TOP_K_RESULTS` to retrieve fewer chunks

### Poor answer quality
- TinyLlama (1.1B params) is limited - consider upgrading to:
  - `mistral` (7B) - Better quality, still local
  - `claude-3-5-sonnet` - Best quality, requires API key
- Improve chunking: adjust `CHUNK_SIZE` and `CHUNK_OVERLAP`

## License

MIT License - Feel free to use and modify!

---

Built with ❤️ by TCA Team
