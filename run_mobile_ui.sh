#!/bin/bash

echo "🚀 Starting TCBot Frontend (React Native)..."

if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed!"
    echo "   The Mobile UI requires Node.js."
    echo "   Please download it from https://nodejs.org/"
    echo ""
    echo "💡 GOOD NEWS: You can use the Web UI instead!"
    echo "   Just open http://localhost:8000 in your browser."
    exit 1
fi

cd frontend
echo "📦 Installing dependencies..."
npm install

echo "📱 Starting Expo..."
echo "   Press 'w' in the next prompt to open in Web Browser,"
echo "   or scan the QR code with your phone."
npx expo start
