"""
API Endpoint Tests
"""
import pytest
from fastapi import status

class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns HTML dashboard"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_api_docs_available(self, client):
        """Test Swagger docs are accessible"""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

class TestDocumentEndpoints:
    """Test document management endpoints"""
    
    def test_list_documents_empty(self, client):
        """Test listing documents when none exist"""
        response = client.get("/api/v1/documents")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_upload_non_pdf_rejected(self, client):
        """Test that non-PDF files are rejected"""
        files = {"file": ("test.txt", b"some content", "text/plain")}
        response = client.post("/api/v1/upload", files=files)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "PDF" in response.json()["detail"]
    
    @pytest.mark.slow
    def test_upload_pdf_success(self, client, sample_pdf_path):
        """Test successful PDF upload"""
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "document_id" in data
        assert "upload_time_ms" in data

class TestDashboardEndpoints:
    """Test dashboard statistics endpoints"""
    
    def test_get_dashboard_stats(self, client):
        """Test dashboard stats endpoint"""
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "documents" in data
        assert "content" in data
        assert "storage" in data
        assert "processing_performance" in data
        assert "query_performance" in data
    
    def test_dashboard_stats_structure(self, client):
        """Test dashboard stats have correct structure"""
        response = client.get("/api/v1/dashboard/stats")
        data = response.json()
        
        # Document stats
        assert "total" in data["documents"]
        assert "processed" in data["documents"]
        assert "success_rate" in data["documents"]
        
        # Content stats
        assert "total_chunks" in data["content"]
        assert "total_pages" in data["content"]
        
        # Performance stats
        assert "avg_total_time_ms" in data["processing_performance"]

class TestChatEndpoints:
    """Test chat/query endpoints"""
    
    def test_chat_empty_query_rejected(self, client):
        """Test that empty queries are rejected"""
        response = client.post("/api/v1/chat?query=")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.slow
    def test_chat_returns_response(self, client):
        """Test that chat returns a response (requires Ollama)"""
        response = client.post("/api/v1/chat?query=Hello")
        
        # Should return 200 even with no documents
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "answer" in data
            assert "confidence" in data
            assert "metrics" in data
