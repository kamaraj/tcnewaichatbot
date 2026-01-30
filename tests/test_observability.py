"""
Observability and Metrics Tests
"""
import pytest

class TestObservability:
    """Test observability setup"""
    
    def test_import_observability(self):
        """Test observability module imports correctly"""
        try:
            from app.observability import (
                tracer, meter,
                DOCUMENTS_UPLOADED, DOCUMENTS_PROCESSED,
                QUERIES_TOTAL, QUERY_LATENCY,
                setup_telemetry, get_metrics_endpoint
            )
            assert tracer is not None
            assert meter is not None
        except ImportError as e:
            pytest.skip(f"OpenTelemetry not installed: {e}")
    
    def test_prometheus_counters_exist(self):
        """Test Prometheus counters are defined"""
        try:
            from app.observability import (
                DOCUMENTS_UPLOADED,
                DOCUMENTS_PROCESSED,
                QUERIES_TOTAL
            )
            assert DOCUMENTS_UPLOADED is not None
            assert DOCUMENTS_PROCESSED is not None
            assert QUERIES_TOTAL is not None
        except ImportError as e:
            pytest.skip(f"Observability not installed: {e}")
    
    def test_prometheus_histograms_exist(self):
        """Test Prometheus histograms are defined"""
        try:
            from app.observability import (
                DOCUMENT_PROCESSING_TIME,
                QUERY_LATENCY,
                CHUNKS_RETRIEVED
            )
            assert DOCUMENT_PROCESSING_TIME is not None
            assert QUERY_LATENCY is not None
            assert CHUNKS_RETRIEVED is not None
        except ImportError as e:
            pytest.skip(f"Observability not installed: {e}")
    
    def test_record_document_upload(self):
        """Test recording document upload metrics"""
        try:
            from app.observability import record_document_upload
            # Should not raise
            record_document_upload(success=True)
            record_document_upload(success=False)
        except ImportError as e:
            pytest.skip(f"Observability not installed: {e}")
    
    def test_record_document_processed(self):
        """Test recording document processed metrics"""
        try:
            from app.observability import record_document_processed
            times = {"chunking": 100, "embedding": 500, "total": 600}
            record_document_processed(success=True, chunks=25, times=times)
        except ImportError as e:
            pytest.skip(f"Observability not installed: {e}")
    
    def test_record_query(self):
        """Test recording query metrics"""
        try:
            from app.observability import record_query
            times = {"retrieval": 200, "generation": 5000, "total": 5200}
            record_query(persona="analyst", confidence="high", times=times, chunks_retrieved=5)
        except ImportError as e:
            pytest.skip(f"Observability not installed: {e}")
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint returns Prometheus format"""
        try:
            from app.observability import get_metrics_endpoint
            response = get_metrics_endpoint()
            assert response is not None
            assert response.status_code == 200
        except ImportError as e:
            pytest.skip(f"Observability not installed: {e}")

class TestTracing:
    """Test OpenTelemetry tracing"""
    
    def test_tracer_available(self):
        """Test tracer is available"""
        try:
            from app.observability import tracer
            assert tracer is not None
        except ImportError as e:
            pytest.skip(f"OpenTelemetry not installed: {e}")
    
    def test_trace_functions_exist(self):
        """Test tracing functions exist"""
        try:
            from app.observability import trace_document_upload, trace_query
            assert trace_document_upload is not None
            assert trace_query is not None
        except ImportError as e:
            pytest.skip(f"OpenTelemetry not installed: {e}")

class TestMetricsIntegration:
    """Integration tests for metrics collection"""
    
    def test_health_endpoint(self, client):
        """Test health endpoint is accessible"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
