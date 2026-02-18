import fitz  # PyMuPDF

def extract_pdf_text(filepath):
    try:
        doc = fitz.open(filepath)
        text = []
        for page in doc:
            page_text = page.get_text().strip()
            if page_text:
                text.append(page_text)
        return '\n\n'.join(text)
    except Exception as e:
        print(f"[ERROR] Extraction failed: {filepath} ({e})")
        return ""
