#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up TCBot locally..."

# Check for Xcode tools/python availability
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: 'python3' is not accessible." 
    echo "   On macOS, this usually means the Xcode Command Line Tools are missing."
    echo "   Please look for a system popup to install them, or run 'xcode-select --install' manually."
    exit 1
fi

# Check for Ollama (Optional if using OpenAI)
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Note: 'ollama' command not found."
    echo "   If you are using local LLMs, you need this."
    echo "   If you are using OpenAI, you can ignore this warning."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists."
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Ensure data directories exist
mkdir -p data/uploads data/chroma

echo "✅ Setup complete!"
echo "---------------------------------------------------"
echo "🤖 Ensure Ollama is running:"
echo "   ollama serve"
echo "---------------------------------------------------"
echo "🚀 Starting FastAPI server at http://localhost:8091"

# Run the app
uvicorn app.main:app --host 0.0.0.0 --port 8091 --reload
