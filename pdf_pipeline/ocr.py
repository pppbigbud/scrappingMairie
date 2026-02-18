import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import io

def preprocess_image(img):
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    return img

def ocr_pdf(filepath, lang='fra'):
    doc = fitz.open(filepath)
    ocr_text = []
    for page in doc:
        if page.get_text().strip():
            continue
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes()))
        img = preprocess_image(img)
        try:
            text = pytesseract.image_to_string(img, lang=lang)
        except Exception as e:
            text = ''
        if text.strip():
            ocr_text.append(text.strip())
    return '\n\n'.join(ocr_text)
