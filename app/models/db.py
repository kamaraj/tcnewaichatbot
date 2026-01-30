from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String)
    file_size_bytes = Column(Integer, default=0)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    num_chunks = Column(Integer, default=0)
    num_pages = Column(Integer, default=0)
    
    # Timing metrics
    upload_time_ms = Column(Float, default=0)
    chunking_time_ms = Column(Float, default=0)
    embedding_time_ms = Column(Float, default=0)
    total_processing_time_ms = Column(Float, default=0)
    
    # Error tracking
    error_message = Column(String, nullable=True)

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String)
    response_text = Column(String)
    query_time = Column(DateTime, default=datetime.utcnow)
    
    # Performance metrics
    retrieval_time_ms = Column(Float, default=0)
    generation_time_ms = Column(Float, default=0)
    total_time_ms = Column(Float, default=0)
    num_chunks_retrieved = Column(Integer, default=0)
    
    # Quality indicators
    sources_used = Column(String, nullable=True)  # JSON list of filenames

class SystemMetrics(Base):
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, index=True)
    metric_value = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
engine = create_engine(settings.SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
