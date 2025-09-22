import io
import docx
from unstructured.partition.docx import partition_docx
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridDocxParser:
    """
    Hybrid DOCX parser:
    - Extracts text natively from paragraphs
    - Extracts images separately and applies OCR on each image
    - Falls back to Unstructured OCR only on images if text is low
    """

    def __init__(self, text_threshold: int = 100, enable_ocr: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr = enable_ocr

    def _extract_text_paragraphs(self, doc) -> list[dict]:
        """Extract text blocks from paragraphs."""
        blocks = []
        for idx, para in enumerate(doc.paragraphs, start=1):
            text = para.text.strip()
            if text:
                blocks.append({
                    "type": "text",
                    "text": text,
                    "metadata": {"paragraph": idx, "source": "docx-native"}
                })
        return blocks

    def _extract_images(self, doc) -> list[dict]:
        """Extract inline images from DOCX as placeholders."""
        blocks = []
        for idx, shape in enumerate(doc.inline_shapes, start=1):
            blocks.append({
                "type": "image",
                "image_index": idx,
                "text": "",  # OCR will be applied next
                "metadata": {"source": "docx-image"}
            })
        return blocks

    def _ocr_images(self, content: bytes, image_blocks: list[dict]) -> list[dict]:
        """Apply Unstructured OCR on each image in the DOCX."""
        if not image_blocks:
            return []

        try:
            # Run OCR on entire doc but extract only image-related blocks
            elements = partition_docx(file=io.BytesIO(content), strategy="hi_res")
            ocr_blocks = []
            for el in elements:
                block_type = getattr(el, "category", "text").lower()
                if block_type in ("image", "table", "tabular") or block_type == "text":
                    ocr_blocks.append({
                        "type": block_type,
                        "text": str(el),
                        "metadata": {"source": "unstructured-ocr"}
                    })
            return ocr_blocks
        except Exception as e:
            raise KnowledgeManagementException(
                f"OCR extraction failed on DOCX images: {e}",
                None,
                "HybridDocxParser"
            )

    def parse(self, content: bytes) -> list[dict]:
        try:
            doc = docx.Document(io.BytesIO(content))

            # Step 1: Native extraction
            text_blocks = self._extract_text_paragraphs(doc)
            image_blocks = self._extract_images(doc)

            # Step 2: Check if doc has enough text
            total_text_len = sum(len(b["text"]) for b in text_blocks)

            results = text_blocks.copy()

            # Step 3: Apply OCR on images only if enabled
            if self.enable_ocr and image_blocks:
                ocr_blocks = self._ocr_images(content, image_blocks)
                results.extend(ocr_blocks)
            else:
                results.extend(image_blocks)

            # Step 4: If native text is very low and OCR is enabled, optionally OCR entire doc
            if total_text_len < self.text_threshold and self.enable_ocr:
                logger.info("Low native text detected, running full OCR fallback")
                full_ocr = self._ocr_images(content, [])
                results.extend(full_ocr)

            return results

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse DOCX: {e}",
                None,
                "HybridDocxParser",
            )
