from pptx import Presentation
import io, tempfile, os
from unstructured.partition.pptx import partition_pptx
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridPPTXParser:
    """
    Hybrid PPTX parser:
    - Extracts text from shapes in slides
    - If little text and slide has images → OCR with Unstructured
    """

    def __init__(self, text_threshold: int = 50, enable_ocr_images: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr_images = enable_ocr_images

    def parse(self, content: bytes) -> list[dict]:
        blocks = []
        try:
            prs = Presentation(io.BytesIO(content))
            for idx, slide in enumerate(prs.slides, start=1):
                text = "\n".join([shape.text for shape in slide.shapes if hasattr(shape, "text")]).strip()

                if len(text) > self.text_threshold:
                    blocks.append({"text": text, "metadata": {"slide": idx, "source": "pptx-native"}})
                else:
                    if self.enable_ocr_images:
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                                tmp.write(content)
                                tmp.flush()
                                elements = partition_pptx(filename=tmp.name, strategy="hi_res")
                                os.unlink(tmp.name)
                                for el in elements:
                                    blocks.append({
                                        "text": str(el),
                                        "metadata": {"slide": idx, "source": "unstructured-ocr"}
                                    })
                        except Exception as e:
                            logger.warning(f"OCR fallback failed in pptx slide {idx}: {e}")

            return blocks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse PPTX: {e}",
                None,
                "HybridPPTXParser"
            )
