"""Utility functions for extracting and filtering dates from documents"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import requests
from email.utils import parsedate_to_datetime

def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Extract date from filename using common patterns.
    
    Patterns supported:
    - 2024-09-10 (ISO format)
    - 09-10-2024 (DD-MM-YYYY)
    - 2024_09_10 (underscore separator)
    - 20240910 (compact)
    - JANV-2026, DEC-2025 (month-year)
    """
    
    # Pattern 1: ISO format YYYY-MM-DD or YYYY_MM_DD
    match = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', filename)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    
    # Pattern 2: Compact YYYYMMDD
    match = re.search(r'(\d{8})', filename)
    if match:
        try:
            date_str = match.group(1)
            return datetime(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))
        except ValueError:
            pass
    
    # Pattern 3: Month-Year format (JANV-2026, DEC-2025, etc.)
    month_map = {
        'janv': 1, 'jan': 1, 'janvier': 1,
        'fev': 2, 'fevr': 2, 'février': 2, 'fevrier': 2,
        'mars': 3, 'mar': 3,
        'avr': 4, 'avril': 4,
        'mai': 5, 'may': 5,
        'juin': 6, 'jun': 6,
        'juil': 7, 'juillet': 7, 'jul': 7,
        'aout': 8, 'août': 8, 'aug': 8,
        'sept': 9, 'sep': 9, 'septembre': 9,
        'oct': 10, 'octobre': 10,
        'nov': 11, 'novembre': 11,
        'dec': 12, 'déc': 12, 'decembre': 12, 'décembre': 12
    }
    
    for month_name, month_num in month_map.items():
        pattern = rf'{month_name}[-_\s]*(\d{{4}})'
        match = re.search(pattern, filename.lower())
        if match:
            try:
                year = int(match.group(1))
                # Use middle of month as default day
                return datetime(year, month_num, 15)
            except ValueError:
                pass
    
    # Pattern 4: MM-YYYY or MM_YYYY format (Nivigne-09-2025.pdf)
    match = re.search(r'[-_](\d{2})[-_](\d{4})', filename)
    if match:
        try:
            month = int(match.group(1))
            year = int(match.group(2))
            if 1 <= month <= 12:
                return datetime(year, month, 15)
        except ValueError:
            pass
    
    # Pattern 5: Year only (use as fallback - least precise)
    match = re.search(r'\b(20\d{2})\b', filename)
    if match:
        try:
            year = int(match.group(1))
            # Use January as default (more likely to be in date ranges than June)
            return datetime(year, 1, 15)
        except ValueError:
            pass
    
    return None

def is_date_in_range(doc_date: Optional[datetime], start_date: Optional[str], end_date: Optional[str]) -> bool:
    """
    Check if document date falls within the specified range.
    
    Args:
        doc_date: Document date (can be None)
        start_date: Start date string in YYYY-MM-DD format (can be None)
        end_date: End date string in YYYY-MM-DD format (can be None)
    
    Returns:
        True if date is in range or if no filtering is needed, False otherwise
    """
    
    # If no date filtering is configured, accept all documents
    if not start_date and not end_date:
        return True
    
    # If document has no date, ACCEPT it (let AI decide relevance later)
    # This is more lenient - we prefer false positives over false negatives
    if doc_date is None:
        return True
    
    # Parse filter dates
    try:
        if start_date:
            filter_start = datetime.fromisoformat(start_date)
            if doc_date < filter_start:
                return False
        
        if end_date:
            filter_end = datetime.fromisoformat(end_date)
            # Add one day to include the end date
            filter_end = filter_end + timedelta(days=1)
            if doc_date >= filter_end:
                return False
        
        return True
    except ValueError:
        # If date parsing fails, accept the document
        return True

def get_pdf_metadata_date(pdf_url: str, session=None) -> Optional[datetime]:
    """
    Get PDF modification date from HTTP headers without downloading the full file.
    Uses HEAD request to get Last-Modified header.
    
    Args:
        pdf_url: URL of the PDF
        session: Optional requests session to reuse
    
    Returns:
        datetime object from Last-Modified header (timezone-naive), or None if not available
    """
    try:
        if session is None:
            session = requests.Session()
        
        # HEAD request to get headers without downloading content
        response = session.head(pdf_url, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            # Try Last-Modified header
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                try:
                    dt = parsedate_to_datetime(last_modified)
                    # Convert to timezone-naive for comparison
                    return dt.replace(tzinfo=None) if dt else None
                except Exception:
                    pass
            
            # Try Date header as fallback
            date_header = response.headers.get('Date')
            if date_header:
                try:
                    dt = parsedate_to_datetime(date_header)
                    # Convert to timezone-naive for comparison
                    return dt.replace(tzinfo=None) if dt else None
                except Exception:
                    pass
        
        return None
    except Exception:
        return None

def get_date_confidence(filename: str) -> str:
    """
    Determine confidence level of date extraction from filename
    
    Returns:
        'high': YYYY-MM-DD format (precise date)
        'medium': MM-YYYY or Month-YYYY format (approximate month)
        'low': YYYY only (year only, very approximate)
        'none': No date found
    """
    # High confidence: ISO format or compact YYYYMMDD
    if re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', filename):
        return 'high'
    if re.search(r'(\d{8})', filename):
        return 'high'
    
    # Medium confidence: Month name or MM-YYYY
    month_names = ['janv', 'jan', 'fev', 'fevr', 'mars', 'mar', 'avr', 'avril', 'mai', 'may',
                   'juin', 'jun', 'juil', 'juillet', 'jul', 'aout', 'août', 'aug',
                   'sept', 'sep', 'oct', 'octobre', 'nov', 'novembre', 'dec', 'déc', 'decembre']
    for month in month_names:
        if re.search(rf'{month}[-_\s]*(\d{{4}})', filename.lower()):
            return 'medium'
    if re.search(r'[-_](\d{2})[-_](\d{4})', filename):
        return 'medium'
    
    # Low confidence: Year only
    if re.search(r'\b(20\d{2})\b', filename):
        return 'low'
    
    return 'none'

def get_most_precise_date(filename: str, pdf_url: str, session=None) -> Tuple[Optional[datetime], str, str]:
    """
    Get the most precise date from both filename and PDF metadata.
    
    Args:
        filename: Name of the PDF file
        pdf_url: URL of the PDF
        session: Optional requests session to reuse
    
    Returns:
        Tuple of (most_precise_date, source, confidence) where:
        - source is 'metadata', 'filename', or 'none'
        - confidence is 'high', 'medium', 'low', or 'none'
    """
    # Extract date from filename
    filename_date = extract_date_from_filename(filename)
    confidence = get_date_confidence(filename)
    
    # Get date from PDF metadata
    metadata_date = get_pdf_metadata_date(pdf_url, session)
    
    # Determine most precise date
    # PRIORITIZE filename over metadata because many servers return current date in metadata
    # instead of actual document date
    if filename_date:
        return (filename_date, 'filename', confidence)
    elif metadata_date:
        return (metadata_date, 'metadata', 'medium')  # Metadata is medium confidence
    else:
        return (None, 'none', 'none')

def format_date_for_display(doc_date: Optional[datetime]) -> str:
    """Format date for display in UI"""
    if doc_date is None:
        return "Date inconnue"
    
    return doc_date.strftime("%d/%m/%Y")
