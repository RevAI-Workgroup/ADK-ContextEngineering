#!/bin/bash
# Helper script to start the FastAPI backend with the correct virtual environment

cd "$(dirname "$0")"

if [ ! -f venv/bin/activate ]; then
  echo "❌ Error: Virtual environment not found at venv/bin/activate"
  echo "Please run: python -m venv venv"
  exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to include project root for proper imports
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start FastAPI backend
echo "🚀 Starting FastAPI backend on http://localhost:8000"
echo "📚 API docs will be available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

