"""
OpenTelemetry Instrumentation and Observability Setup
"""
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resource for identifying the service
resource = Resource.create({
    "service.name": "tcbot-rag",
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

# Trace Provider
trace_provider = TracerProvider(resource=resource)
# trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter())) # Commented out to reduce noise
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# Metrics Provider
metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60000)
# meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader]) # Commented out to reduce nose
meter_provider = MeterProvider(resource=resource, metric_readers=[]) 
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# ==================== PROMETHEUS METRICS ====================

# Document Metrics
DOCUMENTS_UPLOADED = Counter(
    'tcbot_documents_uploaded_total',
    'Total number of documents uploaded',
    ['status']  # success, failed
)

DOCUMENTS_PROCESSED = Counter(
    'tcbot_documents_processed_total',
    'Total number of documents processed',
    ['status']
)

DOCUMENT_PROCESSING_TIME = Histogram(
    'tcbot_document_processing_seconds',
    'Time spent processing documents',
    ['phase'],  # chunking, embedding, total
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

DOCUMENT_CHUNKS = Histogram(
    'tcbot_document_chunks',
    'Number of chunks per document',
    buckets=[10, 25, 50, 100, 250, 500, 1000]
)

# Query Metrics
QUERIES_TOTAL = Counter(
    'tcbot_queries_total',
    'Total number of chat queries',
    ['persona', 'confidence']  # persona type, response confidence
)

QUERY_LATENCY = Histogram(
    'tcbot_query_latency_seconds',
    'Query response latency',
    ['phase'],  # retrieval, generation, total
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

CHUNKS_RETRIEVED = Histogram(
    'tcbot_chunks_retrieved',
    'Number of chunks retrieved per query',
    buckets=[1, 2, 3, 5, 10, 15, 20]
)

# System Metrics
ACTIVE_USERS = Gauge(
    'tcbot_active_users',
    'Number of currently active users'
)

VECTOR_STORE_SIZE = Gauge(
    'tcbot_vector_store_documents',
    'Number of documents in vector store'
)

# ==================== INSTRUMENTATION ====================

def setup_telemetry(app, engine=None):
    """Setup OpenTelemetry instrumentation for FastAPI and SQLAlchemy"""
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented with OpenTelemetry")
    
    # Instrument SQLAlchemy if engine provided
    if engine:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumented with OpenTelemetry")

def get_metrics_endpoint():
    """Return Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# ==================== CUSTOM SPANS ====================

def trace_document_upload(filename: str, file_size: int):
    """Create a span for document upload"""
    with tracer.start_as_current_span("document_upload") as span:
        span.set_attribute("document.filename", filename)
        span.set_attribute("document.size_bytes", file_size)
        return span

def trace_document_processing(doc_id: int, phase: str):
    """Create a span for document processing phases"""
    with tracer.start_as_current_span(f"document_processing.{phase}") as span:
        span.set_attribute("document.id", doc_id)
        span.set_attribute("processing.phase", phase)
        return span

def trace_query(query: str, persona: str = "default"):
    """Create a span for chat queries"""
    with tracer.start_as_current_span("chat_query") as span:
        span.set_attribute("query.text", query[:100])  # Truncate for safety
        span.set_attribute("query.persona", persona)
        return span

# ==================== METRIC HELPERS ====================

def record_document_upload(success: bool):
    """Record document upload metrics"""
    DOCUMENTS_UPLOADED.labels(status="success" if success else "failed").inc()

def record_document_processed(success: bool, chunks: int, times: dict):
    """Record document processing metrics"""
    DOCUMENTS_PROCESSED.labels(status="success" if success else "failed").inc()
    DOCUMENT_CHUNKS.observe(chunks)
    
    if times:
        DOCUMENT_PROCESSING_TIME.labels(phase="chunking").observe(times.get("chunking", 0) / 1000)
        DOCUMENT_PROCESSING_TIME.labels(phase="embedding").observe(times.get("embedding", 0) / 1000)
        DOCUMENT_PROCESSING_TIME.labels(phase="total").observe(times.get("total", 0) / 1000)

def record_query(persona: str, confidence: str, times: dict, chunks_retrieved: int):
    """Record query metrics"""
    QUERIES_TOTAL.labels(persona=persona, confidence=confidence).inc()
    CHUNKS_RETRIEVED.observe(chunks_retrieved)
    
    if times:
        QUERY_LATENCY.labels(phase="retrieval").observe(times.get("retrieval", 0) / 1000)
        QUERY_LATENCY.labels(phase="generation").observe(times.get("generation", 0) / 1000)
        QUERY_LATENCY.labels(phase="total").observe(times.get("total", 0) / 1000)
