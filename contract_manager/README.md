# Contract Manager

A Python-based web application for managing contracts with automatic PDF parsing and OCR capabilities.

## Features

- **PDF Upload & Parsing**: Upload contract PDFs and automatically extract key information
- **OCR Support**: Uses OCR when text extraction fails
- **Data Validation**: Review and correct extracted data before saving
- **REST API**: Clean FastAPI-based backend
- **SQLite Database**: Lightweight database for contract storage
- **Professional UI**: Clean, simple interface with minimal CSS

## Extracted Information

The application extracts the following information from PDFs:

### Client Identity
- Company name
- Full address
- National identifier (SIREN for French companies, Company Number for others)

### Contract Characteristics
- Contract date
- Product/service
- Contract duration (in years)
- Contract value
- ARR (Annual Recurring Revenue) - automatically calculated

## Installation

### Prerequisites

- Python 3.8+
- Tesseract OCR (for OCR functionality)

#### Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install tesseract
brew install poppler
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Setup

1. Navigate to the project directory:
```bash
cd contract_manager
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the FastAPI server:
```bash
cd backend
python main.py
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. **Upload PDF**: Click "Choose PDF File" and select a contract PDF
2. **Review Data**: The app will parse the PDF and display extracted information
3. **Correct/Amend**: Edit any fields that need correction
4. **Save**: Click "Save Contract" to store in the database
5. **View Contracts**: Scroll down to see all saved contracts

## API Endpoints

- `POST /api/upload` - Upload and parse a PDF file
- `POST /api/contracts` - Create a new contract
- `GET /api/contracts` - Get all contracts
- `GET /api/contracts/{id}` - Get a specific contract
- `PUT /api/contracts/{id}` - Update a contract
- `DELETE /api/contracts/{id}` - Delete a contract

## Project Structure

```
contract_manager/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── database.py       # Database models and configuration
│   ├── models.py         # Pydantic models
│   └── pdf_parser.py     # PDF parsing and OCR logic
├── frontend/
│   ├── index.html        # Main HTML page
│   ├── style.css         # Styling
│   └── app.js            # Frontend JavaScript
├── uploads/              # PDF upload directory
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Notes

- The application uses SQLite for simplicity. For production, consider PostgreSQL or MySQL.
- PDF parsing accuracy depends on the quality and structure of the PDF.
- OCR is automatically triggered when text extraction fails.
- All monetary values are displayed in Euros (€) by default.

## Troubleshooting

**OCR not working:**
- Ensure Tesseract OCR is properly installed
- Check that `pytesseract` can find the Tesseract executable

**PDF parsing issues:**
- Some PDFs may have complex layouts that are difficult to parse
- Manual correction is available for all fields

**Import errors:**
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Activate your virtual environment
