"""
Pytest Configuration and Fixtures
"""
import pytest
import asyncio
from typing import Generator
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

# Import app components
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.models.db import Base, get_db

# Test database URL
TEST_DATABASE_URL = "sqlite:///./data/test_db.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    # Ensure fresh start for each test session
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test"""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

class SyncTestClient:
    """Synchronous test client using httpx with async transport"""
    def __init__(self, app):
        self.app = app
        self._transport = httpx.ASGITransport(app=app)
    
    def _make_request(self, method: str, url: str, **kwargs):
        async def _async_request():
            async with httpx.AsyncClient(transport=self._transport, base_url="http://test") as client:
                if method == "GET":
                    return await client.get(url, **kwargs)
                elif method == "POST":
                    return await client.post(url, **kwargs)
                elif method == "PUT":
                    return await client.put(url, **kwargs)
                elif method == "DELETE":
                    return await client.delete(url, **kwargs)
        
        return asyncio.get_event_loop().run_until_complete(_async_request())
    
    def get(self, url, **kwargs):
        return self._make_request("GET", url, **kwargs)
    
    def post(self, url, **kwargs):
        return self._make_request("POST", url, **kwargs)
    
    def put(self, url, **kwargs):
        return self._make_request("PUT", url, **kwargs)
    
    def delete(self, url, **kwargs):
        return self._make_request("DELETE", url, **kwargs)

@pytest.fixture(scope="function")
def client(db_session, event_loop) -> Generator:
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield SyncTestClient(app)
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF for testing"""
    content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test Document) Tj ET
endstream
endobj
xref
0 5
trailer
<< /Root 1 0 R /Size 5 >>
startxref
%%EOF
"""
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests (involve LLM)")
    config.addinivalue_line("markers", "persona: Persona-based tests")
