import io
import docx
from unstructured.partition.docx import partition_docx
from .base import BaseParser
from .utils_image import ocr_image_bytes

class HybridDocxParser(BaseParser):
    def __init__(self, enable_ocr_images: bool = False):
        self.enable_ocr_images = enable_ocr_images

    def _parse_with_unstructured(self, content: bytes) -> list[dict]:
        elements = partition_docx(file=io.BytesIO(content))
        blocks = []
        for idx, el in enumerate(elements, start=1):
            text = str(el).strip()
            if text:
                blocks.append({"text": text, "metadata": {"source": "unstructured-docx", "block": idx}})
        return blocks

    def _parse_with_docx(self, content: bytes) -> list[dict]:
        doc = docx.Document(io.BytesIO(content))
        blocks = []
        for idx, para in enumerate(doc.paragraphs, start=1):
            if para.text.strip():
                blocks.append({"text": para.text, "metadata": {"source": "python-docx", "paragraph": idx}})
        # OCR images if enabled
        if self.enable_ocr_images:
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    img_bytes = rel.target_part.blob
                    ocr_blocks = ocr_image_bytes(img_bytes, "docx-image", {"image": rel.target_ref})
                    blocks.extend(ocr_blocks)
        return blocks

    def parse(self, content: bytes) -> list[dict]:
        try:
            blocks = self._parse_with_unstructured(content)
            if blocks:
                return blocks
        except Exception:
            pass
        return self._parse_with_docx(content)
