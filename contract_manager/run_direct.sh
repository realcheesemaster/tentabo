#!/bin/bash

# Contract Manager startup script (without virtual environment)

echo "Contract Manager - Starting..."
echo ""

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check for required packages
echo "Checking dependencies..."
python3 -c "import fastapi" 2>/dev/null || {
    echo "Installing dependencies..."
    pip3 install --user -r requirements.txt || {
        echo "Error: Failed to install dependencies."
        echo "Try: pip3 install --user -r requirements.txt"
        exit 1
    }
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
echo "Application will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

cd backend
python3 main.py
