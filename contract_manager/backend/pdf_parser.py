import re
from datetime import datetime
from typing import Optional, Dict, Any, List
import PyPDF2
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from dateutil import parser as date_parser


class PDFParser:
    def __init__(self):
        self.patterns = {
            'siren': r'\b\d{9}\b',  # French SIREN (9 digits)
            'siret': r'\b\d{14}\b',  # French SIRET (14 digits)
            'company_number': r'\b(?:Company Number|Registration Number|Reg\.?\s*No\.?|N°\s*SIREN|SIREN|Immatriculation)[:\s]*([A-Z0-9\s]+)\b',
            'currency': r'[€$£¥]\s*[\d\s,]+\.?\d*|\d+[\d\s,]*\.?\d*\s*(?:EUR|USD|GBP|JPY|euros?|€)',
            'duration': r'(\d+)\s*(?:year|yr|an|année|annee|years|ans|month|mois|months)',
        }

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods for best results."""
        text = ""

        # Method 1: Try pdfplumber first (best for structured PDFs)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            if len(text.strip()) > 100:
                print(f"✓ Extracted {len(text)} chars using pdfplumber")
                return text
        except Exception as e:
            print(f"pdfplumber failed: {e}")

        # Method 2: Try PyPDF2 as fallback
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            if len(text.strip()) > 100:
                print(f"✓ Extracted {len(text)} chars using PyPDF2")
                return text
        except Exception as e:
            print(f"PyPDF2 failed: {e}")

        # Method 3: Use enhanced OCR for scanned PDFs
        print("Using OCR (this may take a moment)...")
        text = self._ocr_pdf_enhanced(pdf_path)
        print(f"✓ Extracted {len(text)} chars using OCR")

        return text

    def _ocr_pdf_enhanced(self, pdf_path: str) -> str:
        """Enhanced OCR with image preprocessing for better accuracy."""
        text = ""
        try:
            # Convert PDF to images at lower DPI to reduce memory usage
            # Only process first 5 pages to avoid memory issues
            images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=5)

            for i, image in enumerate(images):
                print(f"  Processing page {i+1}/{len(images)}...")

                # Resize image if too large to reduce memory usage
                max_dimension = 2000
                if image.width > max_dimension or image.height > max_dimension:
                    ratio = min(max_dimension / image.width, max_dimension / image.height)
                    new_size = (int(image.width * ratio), int(image.height * ratio))
                    image = image.resize(new_size, Image.LANCZOS)

                # Preprocess image for better OCR
                processed_image = self._preprocess_image(image)

                # Use only the most reliable Tesseract configuration
                try:
                    page_text = pytesseract.image_to_string(
                        processed_image,
                        lang='eng+fra',  # English + French
                        config='--psm 3'  # Fully automatic page segmentation
                    )
                    text += page_text + "\n"
                except Exception as e:
                    print(f"    OCR failed for page {i+1}: {e}")

                # Clean up to free memory
                del processed_image
                del image

        except Exception as e:
            print(f"OCR error: {e}")

        return text

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy."""
        # Convert PIL Image to OpenCV format
        img_array = np.array(image)

        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Apply adaptive thresholding for better contrast
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Deskew if needed
        binary = self._deskew(binary)

        # Convert back to PIL Image
        processed = Image.fromarray(binary)

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(2.0)

        return processed

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Deskew image to improve OCR accuracy."""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 10:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5:  # Only deskew if angle is significant
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated

    def parse_contract(self, pdf_path: str, filename: str) -> Dict[str, Any]:
        """Parse PDF and extract contract information."""
        text = self.extract_text_from_pdf(pdf_path)

        result = {
            'client_company_name': self._extract_company_name(text),
            'client_company_address': self._extract_address(text),
            'client_national_identifier': self._extract_national_id(text),
            'contract_date': self._extract_date(text),
            'product': self._extract_product(text),
            'contract_duration': self._extract_duration(text),
            'contract_value': self._extract_value(text),
            'filename': filename
        }

        # Calculate ARR
        if result['contract_value'] and result['contract_duration']:
            result['arr'] = round(result['contract_value'] / result['contract_duration'], 2)
        else:
            result['arr'] = None

        return result

    def _extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name (looking for common patterns)."""
        lines = text.split('\n')

        # Look for lines with company indicators
        company_keywords = ['Ltd', 'Limited', 'Inc', 'Corp', 'Corporation',
                           'SA', 'SAS', 'SARL', 'EURL', 'SNC', 'GmbH', 'AG', 'LLC', 'LLP']

        for line in lines[:30]:  # Check first 30 lines
            line = line.strip()
            if any(keyword in line for keyword in company_keywords):
                if 5 < len(line) < 100:  # Reasonable length
                    return line

        # Fallback: return first substantial line
        for line in lines[:15]:
            line = line.strip()
            if line and 5 < len(line) < 100 and not line.startswith(('Page', 'Contract', 'Agreement')):
                return line

        return None

    def _extract_address(self, text: str) -> Optional[str]:
        """Extract address (looking for postal codes and street patterns)."""
        lines = text.split('\n')

        # French postal code pattern
        french_postal = r'\b\d{5}\b'
        # UK postal code pattern
        uk_postal = r'\b[A-Z]{1,2}\d{1,2}\s*\d[A-Z]{2}\b'
        # US ZIP code pattern
        us_postal = r'\b\d{5}(?:-\d{4})?\b'

        # Find lines with postal codes
        for i, line in enumerate(lines):
            if re.search(f'{french_postal}|{uk_postal}|{us_postal}', line, re.IGNORECASE):
                # Build address from surrounding lines
                start = max(0, i - 2)
                end = min(len(lines), i + 2)
                address_lines = [l.strip() for l in lines[start:end] if l.strip()]
                address = ', '.join(address_lines[:4])  # Max 4 lines
                if len(address) > 10:
                    return address

        # Fallback: look for street numbers
        for i, line in enumerate(lines):
            if re.search(r'^\d+\s+[A-Za-z]', line.strip()):
                # Combine with next 1-2 lines
                address_lines = [line.strip()]
                if i + 1 < len(lines):
                    address_lines.append(lines[i + 1].strip())
                if i + 2 < len(lines):
                    address_lines.append(lines[i + 2].strip())
                return ', '.join(address_lines)

        return None

    def _extract_national_id(self, text: str) -> Optional[str]:
        """Extract national identifier (SIREN, SIRET, or Company Number)."""
        # Try SIRET first (14 digits) - more specific than SIREN
        siret_match = re.search(self.patterns['siret'], text)
        if siret_match:
            return siret_match.group(0)

        # Try SIREN pattern (9 digits)
        siren_match = re.search(self.patterns['siren'], text)
        if siren_match:
            return siren_match.group(0)

        # Try company number with label
        company_match = re.search(self.patterns['company_number'], text, re.IGNORECASE)
        if company_match:
            identifier = company_match.group(1).strip()
            # Clean up extra spaces
            identifier = ' '.join(identifier.split())
            return identifier

        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract contract date with improved detection."""
        lines = text.split('\n')

        # Keywords that indicate a contract date
        date_keywords = [
            r'date\s*(?:of|du)?\s*(?:contract|contrat)?',
            r'signed\s*(?:on)?',
            r'signé\s*le',
            r'fait\s*(?:à|a)',
            r'dated',
            r'effective\s*date',
            r'date\s*d\'effet'
        ]

        # First, try to find dates near keywords
        for i, line in enumerate(lines):
            for keyword in date_keywords:
                if re.search(keyword, line, re.IGNORECASE):
                    # Look in current line and next few lines
                    search_text = '\n'.join(lines[i:min(i+3, len(lines))])
                    date_str = self._parse_date_from_text(search_text)
                    if date_str:
                        return date_str

        # Second, try all dates in the document and pick the most likely
        all_dates = []
        for line in lines[:50]:  # Check first 50 lines
            date_str = self._parse_date_from_text(line)
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    # Only accept dates between 1990 and 2050
                    if 1990 <= date_obj.year <= 2050:
                        all_dates.append(date_str)
                except:
                    pass

        # Return the first valid date found
        if all_dates:
            return all_dates[0]

        return None

    def _parse_date_from_text(self, text: str) -> Optional[str]:
        """Parse a date from text using multiple methods."""
        # Method 1: Try dateutil parser (handles many formats)
        try:
            # Extract potential date strings
            words = text.split()
            for i in range(len(words)):
                # Try parsing 1-5 consecutive words as a date
                for length in range(1, min(6, len(words) - i + 1)):
                    date_candidate = ' '.join(words[i:i+length])
                    try:
                        parsed_date = date_parser.parse(date_candidate, fuzzy=True, dayfirst=True)
                        # Validate it's a reasonable date
                        if 1990 <= parsed_date.year <= 2050:
                            return parsed_date.strftime('%Y-%m-%d')
                    except:
                        continue
        except:
            pass

        # Method 2: Regex patterns for common date formats
        date_patterns = [
            # DD/MM/YYYY or DD-MM-YYYY
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', 'dmy'),
            # YYYY-MM-DD or YYYY/MM/DD
            (r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', 'ymd'),
            # DD Month YYYY (e.g., 15 January 2024)
            (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b', 'dmy_text'),
            # Month DD, YYYY (e.g., January 15, 2024)
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{1,2}),?\s+(\d{4})\b', 'mdy_text'),
        ]

        for pattern, format_type in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if format_type == 'dmy':
                        day, month, year = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    elif format_type == 'ymd':
                        year, month, day = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    elif format_type in ['dmy_text', 'mdy_text']:
                        date_str = match.group(0)
                        date_obj = date_parser.parse(date_str, dayfirst=(format_type == 'dmy_text'))

                    if 1990 <= date_obj.year <= 2050:
                        return date_obj.strftime('%Y-%m-%d')
                except:
                    continue

        return None

    def _extract_product(self, text: str) -> Optional[str]:
        """Extract product name (looking for common keywords)."""
        product_keywords = [
            'Product:', 'Service:', 'Software:', 'Subscription:', 'License:',
            'Produit:', 'Service:', 'Logiciel:', 'Abonnement:', 'Licence:'
        ]

        lines = text.split('\n')
        for line in lines:
            for keyword in product_keywords:
                if keyword in line:
                    # Extract text after the keyword
                    parts = line.split(keyword, 1)
                    if len(parts) > 1:
                        product = parts[1].strip()
                        # Clean up and limit length
                        product = product.split('\n')[0]  # Take only first line
                        if product:
                            return product[:100]

        return None

    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract contract duration in months."""
        # Look for duration with keywords
        duration_patterns = [
            r'(?:duration|durée|duree|term|période|periode)[:\s]+(\d+)\s*(year|yr|an|année|annee|years|ans|month|mois|months)',
            r'(\d+)\s*(?:year|yr|an|année|annee|years|ans)\s*(?:contract|contrat|term|agreement)',
        ]

        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    number = int(match.group(1))
                    unit = match.group(2).lower() if len(match.groups()) > 1 else match.group(0).lower()

                    # Check if it's months or years
                    if 'month' in unit or 'mois' in unit:
                        return number  # Already in months
                    else:
                        return number * 12  # Convert years to months
                except:
                    pass

        # Fallback to original pattern
        matches = re.findall(self.patterns['duration'], text, re.IGNORECASE)
        if matches:
            for match in matches:
                try:
                    number = int(match)
                    # Look around the number for month/year indicators
                    pattern_with_context = rf'{number}\s*(\w+)'
                    context_match = re.search(pattern_with_context, text)
                    if context_match:
                        unit = context_match.group(1).lower()
                        if 'month' in unit or 'mois' in unit:
                            return number  # Already in months
                        else:
                            return number * 12  # Convert years to months
                except:
                    continue

        return None

    def _extract_value(self, text: str) -> Optional[float]:
        """Extract contract value."""
        # Look for amounts with keywords
        value_keywords = [
            r'(?:total|montant|amount|value|valeur|price|prix)[:\s]*([€$£¥]?\s*[\d\s,]+\.?\d*)\s*(?:EUR|USD|GBP|JPY|euros?|€)?',
        ]

        for pattern in value_keywords:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                value = self._parse_currency_value(amount_str)
                if value and value > 100:
                    return value

        # Fallback: find all currency values and take the largest reasonable one
        currency_matches = re.findall(self.patterns['currency'], text)
        values = []

        for match in currency_matches:
            value = self._parse_currency_value(match)
            if value and 100 < value < 10000000:  # Reasonable contract value range
                values.append(value)

        if values:
            # Return the largest value (likely the total contract value)
            return max(values)

        return None

    def _parse_currency_value(self, text: str) -> Optional[float]:
        """Parse a currency value from text."""
        # Remove currency symbols and letters
        number_str = re.sub(r'[€$£¥EUR USD GBP JPY euros?,\s]', '', text, flags=re.IGNORECASE).strip()

        try:
            value = float(number_str)
            return value
        except ValueError:
            return None
