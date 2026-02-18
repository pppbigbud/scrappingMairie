"""
OCR processor for scanned PDFs
Extracts text from image-based PDFs using Tesseract OCR
"""

import io
import os
from typing import Optional
import pdfplumber

def is_scanned_pdf(pdf_content: bytes) -> bool:
    """
    Detect if a PDF is scanned (image-based) or text-based
    
    Args:
        pdf_content: PDF file content as bytes
    
    Returns:
        True if PDF appears to be scanned
    """
    try:
        pdf_file = io.BytesIO(pdf_content)
        
        with pdfplumber.open(pdf_file) as pdf:
            # Check first 3 pages
            pages_to_check = min(3, len(pdf.pages))
            
            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text()
                
                # If we find substantial text, it's not scanned
                if text and len(text.strip()) > 100:
                    return False
            
            # If no text found in first pages, likely scanned
            return True
            
    except Exception:
        # If we can't determine, assume not scanned
        return False

def extract_text_with_ocr(pdf_content: bytes, pdf_name: str = "unknown") -> Optional[str]:
    """
    Extract text from scanned PDF using OCR with enhanced quality
    
    Args:
        pdf_content: PDF file content as bytes
        pdf_name: Name of PDF for logging
    
    Returns:
        Extracted text or None if OCR fails
    """
    try:
        # Check if tesseract is installed
        import pytesseract
        from pdf2image import convert_from_bytes
        from PIL import Image, ImageEnhance, ImageFilter
        
        print(f"[OCR] Starting OCR extraction for {pdf_name}...")
        
        # Convert PDF to images with higher DPI for better quality
        images = convert_from_bytes(
            pdf_content, 
            dpi=400,  # Increased from 300 to 400 for better quality
            fmt='png',
            thread_count=2
        )
        
        print(f"[OCR] Converted {len(images)} pages to images")
        
        extracted_text = []
        
        # OCR each page with preprocessing
        for i, image in enumerate(images):
            # Preprocess image for better OCR
            # Convert to grayscale
            image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Sharpen image
            image = image.filter(ImageFilter.SHARPEN)
            
            # Perform OCR with French language and custom config
            # PSM 3 = Fully automatic page segmentation (default)
            # OEM 3 = Default, based on what is available (LSTM + Legacy)
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(
                image, 
                lang='fra+eng',  # French + English for better coverage
                config=custom_config
            )
            
            if text.strip():
                extracted_text.append(f"--- Page {i+1} ---\n{text}")
                print(f"[OCR] Page {i+1}: Extracted {len(text)} characters")
            else:
                print(f"[OCR] Page {i+1}: No text extracted")
        
        result = '\n\n'.join(extracted_text)
        print(f"[OCR] Total extracted: {len(result)} characters from {len(extracted_text)} pages")
        return result if result.strip() else None
        
    except ImportError as e:
        print(f"[OCR] Error: Missing dependency - {e}")
        print("[OCR] Install with: brew install tesseract tesseract-lang")
        print("[OCR] And: pip install pytesseract pdf2image pillow")
        return None
    except Exception as e:
        print(f"[OCR] Extraction failed for {pdf_name}: {e}")
        return None

def extract_pdf_with_fallback(pdf_content: bytes) -> Optional[str]:
    """
    Extract text from PDF with OCR fallback for scanned PDFs
    
    Args:
        pdf_content: PDF file content as bytes
    
    Returns:
        Extracted text
    """
    try:
        # First try normal text extraction
        pdf_file = io.BytesIO(pdf_content)
        
        with pdfplumber.open(pdf_file) as pdf:
            text_parts = []
            
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            combined_text = '\n\n'.join(text_parts)
            
            # If we got substantial text, return it
            if len(combined_text.strip()) > 100:
                print(f"[PDF] Extracted {len(combined_text)} characters using standard extraction")
                return combined_text
            
            # Otherwise, try OCR
            print(f"[PDF] Only {len(combined_text.strip())} characters extracted, attempting OCR...")
            ocr_text = extract_text_with_ocr(pdf_content, "PDF")
            
            if ocr_text and len(ocr_text.strip()) > 50:
                print(f"[PDF] OCR successful: {len(ocr_text)} characters")
                return ocr_text
            
            # If OCR failed or returned little text, return what we have
            if combined_text.strip():
                print(f"[PDF] OCR failed, returning {len(combined_text)} characters from standard extraction")
                return combined_text
            else:
                print("[PDF] No text could be extracted (empty or unreadable PDF)")
                return None
            
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return None

def check_tesseract_installed() -> bool:
    """Check if Tesseract OCR is installed"""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except:
        return False

def install_instructions() -> str:
    """Get installation instructions for Tesseract"""
    return """
    Pour installer Tesseract OCR sur Mac:
    
    1. Installer Tesseract:
       brew install tesseract
    
    2. Installer le pack de langue française:
       brew install tesseract-lang
    
    3. Vérifier l'installation:
       tesseract --version
    """
