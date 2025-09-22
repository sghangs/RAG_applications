from pptx import Presentation
import io
from unstructured.partition.pptx import partition_pptx
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridPPTXParser:
    """
    Hybrid PPTX parser:
    - Extracts text from shapes in slides
    - Applies OCR only on images
    - Falls back to full slide OCR only if text is very low
    """

    def __init__(self, text_threshold: int = 50, enable_ocr: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr = enable_ocr

    def _extract_slide_text(self, slide) -> str:
        """Extract text from all shapes in a slide."""
        texts = [shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
        return "\n".join(texts).strip()

    def _extract_images(self, slide) -> list[dict]:
        """Return placeholders for images in the slide (OCR applied later)."""
        image_blocks = []
        for idx, shape in enumerate(slide.shapes, start=1):
            if shape.shape_type == 13:  # PICTURE
                image_blocks.append({
                    "type": "image",
                    "image_index": idx,
                    "text": "",
                    "metadata": {"source": "pptx-image"}
                })
        return image_blocks

    def _ocr_images(self, content: bytes, image_blocks: list[dict]) -> list[dict]:
        """Apply OCR on images using Unstructured."""
        if not image_blocks:
            return []

        try:
            elements = partition_pptx(file=io.BytesIO(content), strategy="hi_res")
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
                f"OCR extraction failed on PPTX images: {e}",
                None,
                "HybridPPTXParser"
            )

    def parse(self, content: bytes) -> list[dict]:
        try:
            prs = Presentation(io.BytesIO(content))
            results = []

            for slide_idx, slide in enumerate(prs.slides, start=1):
                slide_text = self._extract_slide_text(slide)
                image_blocks = self._extract_images(slide)

                # Native text block
                if slide_text:
                    results.append({
                        "type": "text",
                        "text": slide_text,
                        "metadata": {"slide": slide_idx, "source": "pptx-native"}
                    })

                # OCR on images
                if self.enable_ocr and image_blocks:
                    ocr_blocks = self._ocr_images(content, image_blocks)
                    results.extend(ocr_blocks)
                else:
                    results.extend(image_blocks)

                # Full slide OCR fallback if native text very low
                if len(slide_text) < self.text_threshold and self.enable_ocr:
                    logger.info(f"Low text in slide {slide_idx}, applying full OCR fallback")
                    full_ocr = self._ocr_images(content, [])
                    results.extend(full_ocr)

            return results

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse PPTX: {e}",
                None,
                "HybridPPTXParser"
            )
