#!/bin/bash
# Run Tests Script

set -e

echo "=============================================="
echo "  TCBot RAG - Test Suite"
echo "=============================================="

# Activate virtual environment
source venv/bin/activate

# Install test dependencies if needed
echo "📦 Checking test dependencies..."
pip install pytest pytest-asyncio pytest-cov httpx faker --quiet

echo ""
echo "🧪 Running all tests..."
echo "----------------------------------------------"

# Run tests with different options based on argument
case "${1:-all}" in
    "unit")
        echo "Running unit tests only..."
        pytest tests/ -m "unit" -v
        ;;
    "integration")
        echo "Running integration tests..."
        pytest tests/ -m "integration" -v
        ;;
    "persona")
        echo "Running persona-based tests..."
        pytest tests/ -m "persona" -v
        ;;
    "fast")
        echo "Running fast tests (excluding slow)..."
        pytest tests/ -m "not slow" -v
        ;;
    "coverage")
        echo "Running tests with coverage..."
        pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v
        echo ""
        echo "📊 Coverage report generated in htmlcov/"
        ;;
    "all")
        echo "Running all tests..."
        pytest tests/ -v
        ;;
    *)
        echo "Usage: $0 [unit|integration|persona|fast|coverage|all]"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "✅ Tests completed!"
echo "=============================================="
