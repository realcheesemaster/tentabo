#!/bin/bash

# Contract Manager startup script

echo "Contract Manager - Starting..."
echo ""

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv || {
        echo "Error: Failed to create virtual environment."
        echo "On Debian/Ubuntu, you may need to run: sudo apt install python3-venv"
        exit 1
    }
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || {
    echo "Error: Failed to activate virtual environment."
    exit 1
}

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt || {
    echo "Error: Failed to install dependencies."
    exit 1
}

# Check for Tesseract
if ! command -v tesseract &> /dev/null; then
    echo ""
    echo "Warning: Tesseract OCR is not installed."
    echo "OCR functionality will not work."
    echo "To install:"
    echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr poppler-utils"
    echo "  macOS: brew install tesseract poppler"
    echo ""
fi

# Start the application
echo ""
echo "Starting Contract Manager..."
echo "Application will be available at: http://10.0.0.1:8000"
echo ""

cd backend
python3 main.py
