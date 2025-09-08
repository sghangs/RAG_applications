import io
from typing import List, Dict

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None


def ocr_image_bytes(img_bytes: bytes, source: str, meta: dict) -> List[Dict]:
    """Run OCR on image bytes and return text blocks with metadata"""
    if not pytesseract:
        return []
    image = Image.open(io.BytesIO(img_bytes))
    text = pytesseract.image_to_string(image)
    if text.strip():
        return [{"text": text, "metadata": {**meta, "source": source, "type": "image-ocr"}}]
    return []
