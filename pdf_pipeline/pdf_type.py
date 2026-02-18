import fitz  # PyMuPDF

def detect_pdf_type(filepath):
    try:
        doc = fitz.open(filepath)
        if doc.page_count == 0:
            return 'vide'
        for page in doc:
            text = page.get_text().strip()
            if text:
                return 'texte'
        return 'scanne'
    except Exception as e:
        if 'password' in str(e).lower():
            return 'protégé'
        return 'corrompu'
