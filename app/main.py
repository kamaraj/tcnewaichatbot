from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.config import settings
from app.models.db import init_db, engine

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise RAG AI Platform with Observability",
    version="1.0.0"
)

# Enable CORS (Must be added before instrumentation in some cases)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://127.0.0.1:8081", "http://localhost:8091", "http://127.0.0.1:8091"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== OBSERVABILITY ====================
try:
    from app.observability import (
        setup_telemetry, get_metrics_endpoint,
        record_document_upload, record_query
    )
    
    # Setup OpenTelemetry instrumentation
    setup_telemetry(app, engine)
    
    @app.get("/metrics")
    def metrics():
        """Prometheus metrics endpoint"""
        return get_metrics_endpoint()
    
    OBSERVABILITY_ENABLED = True
except ImportError as e:
    print(f"Observability not fully configured: {e}")
    OBSERVABILITY_ENABLED = False

# ==================== STARTUP ====================
@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ Database initialized")
    if OBSERVABILITY_ENABLED:
        print("✅ OpenTelemetry instrumentation active")
        print("✅ Prometheus metrics available at /metrics")

# ==================== ROUTES ====================
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")

@app.get("/chat")
def read_chat():
    response = FileResponse("app/static/chat.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "observability": OBSERVABILITY_ENABLED
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8091, reload=True)
