# Installation Guide

## Quick Start

### Option 1: Using the startup script (Recommended)

```bash
cd contract_manager
./run.sh
```

The script will:
- Create a virtual environment
- Install all dependencies
- Start the application
- Open it at http://localhost:8000

### Option 2: Manual installation

1. **Install system dependencies** (required for OCR):

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-venv tesseract-ocr poppler-utils
   ```

   **macOS:**
   ```bash
   brew install tesseract poppler
   ```

2. **Create and activate virtual environment:**
   ```bash
   cd contract_manager
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   cd backend
   python3 main.py
   ```

5. **Access the application:**
   Open your browser to: http://localhost:8000

## Troubleshooting

### Python virtual environment error
If you get an error creating the virtual environment:
```bash
sudo apt install python3.13-venv
# or for your specific Python version
```

### Tesseract not found
OCR will not work without Tesseract. Install it with:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils

# macOS
brew install tesseract poppler
```

### Port already in use
If port 8000 is already in use, edit `backend/main.py` and change:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```
to a different port number.

## Next Steps

Once installed, see README.md for usage instructions.
