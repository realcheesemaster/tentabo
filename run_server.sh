#!/bin/bash
# Start Tentabo PRM API Server

echo "Starting Tentabo PRM API Server..."
echo "=================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "Creating .env from .env.auth template..."
    cp .env.auth .env
    echo "Please edit .env with your configuration"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if dependencies are installed
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Dependencies not installed"
    echo "Run: pip install -r requirements.txt"
    exit 1
fi

# Start server
echo "Starting server on http://localhost:8000"
echo "API documentation: http://localhost:8000/api/docs"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
