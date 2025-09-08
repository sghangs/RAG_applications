import docx
import io
import tempfile
import os
from unstructured.partition.docx import partition_docx
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridDocxParser:
    """
    Hybrid DOCX parser:
    - Extracts text natively from docx paragraphs
    - If a paragraph has very little/no text but images exist, uses OCR (via Unstructured)
    """

    def __init__(self, text_threshold: int = 30, enable_ocr_images: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr_images = enable_ocr_images

    def parse(self, content: bytes) -> list[dict]:
        blocks = []
        try:
            doc = docx.Document(io.BytesIO(content))

            for idx, para in enumerate(doc.paragraphs, start=1):
                if len(para.text.strip()) > self.text_threshold:
                    blocks.append({
                        "text": para.text.strip(),
                        "metadata": {"paragraph": idx, "source": "docx-native"}
                    })
                else:
                    if self.enable_ocr_images:
                        # fallback OCR on images in docx
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                                tmp.write(content)
                                tmp.flush()
                                elements = partition_docx(filename=tmp.name, strategy="hi_res")
                                os.unlink(tmp.name)
                                for el in elements:
                                    blocks.append({
                                        "text": str(el),
                                        "metadata": {"paragraph": idx, "source": "unstructured-ocr"}
                                    })
                        except Exception as e:
                            logger.warning(f"OCR fallback failed in docx paragraph {idx}: {e}")

            return blocks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse DOCX: {e}",
                None,
                "HybridDocxParser"
            )
