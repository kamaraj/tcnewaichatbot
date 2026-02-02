# API Handler for Vercel
# This file wraps the FastAPI app for Vercel's serverless functions

from app.main import app

# Vercel expects the handler to be named 'app' or 'handler'
handler = app
