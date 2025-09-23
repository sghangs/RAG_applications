# ingestion/parsers/docx_parser.py
import io
from typing import List, Dict, Any

import docx
from unstructured.partition.docx import partition_docx
from unstructured.partition.image import partition_image
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridDocxParser:
    """
    Hybrid DOCX parser:
    - Extracts text natively from paragraphs
    - Extracts images and runs OCR on each image (in-memory) using Unstructured's partition_image
    - Falls back to full-document Unstructured OCR only if native text is below threshold
    """

    def __init__(self, text_threshold: int = 100, enable_ocr: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr = enable_ocr

    def _extract_text_paragraphs(self, doc: docx.document.Document) -> List[Dict[str, Any]]:
        """Extract text blocks from paragraphs (native)."""
        blocks: List[Dict[str, Any]] = []
        for idx, para in enumerate(doc.paragraphs, start=1):
            text = para.text.strip()
            if text:
                blocks.append({
                    "type": "text",
                    "text": text,
                    "metadata": {"paragraph": idx, "source": "docx-native"}
                })
        return blocks

    def _extract_image_blobs(self, doc: docx.document.Document) -> List[Dict[str, Any]]:
        """
        Extract binary blobs for images embedded in the DOCX.
        Returns list of dicts: {"image_index": int, "blob": bytes, "content_type": str (optional)}
        """
        image_blobs: List[Dict[str, Any]] = []
        try:
            # doc.part.rels contains relationships; image parts usually have 'image' in reltype
            idx = 0
            for rel in doc.part.rels.values():
                # rel.reltype often contains 'image' for image relationships
                if rel.reltype and "image" in rel.reltype:
                    idx += 1
                    try:
                        img_blob = rel.target_part.blob
                    except Exception:
                        # If the relationship doesn't expose blob or is not an image, skip
                        logger.debug("Skipping non-image rel or unreadable blob")
                        continue
                    image_blobs.append({
                        "image_index": idx,
                        "blob": img_blob,
                        "rel_id": getattr(rel, "rId", None)
                    })
        except Exception as e:
            logger.warning(f"Failed to enumerate image parts in DOCX: {e}")
        return image_blobs

    def _ocr_images_only(self, image_blobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        OCR each image blob using Unstructured's partition_image (in-memory).
        Returns list of blocks derived from images (text/table/image_text).
        """
        ocr_blocks: List[Dict[str, Any]] = []
        if not image_blobs:
            return ocr_blocks

        for img in image_blobs:
            img_idx = img.get("image_index")
            blob = img.get("blob")
            if not blob:
                continue

            try:
                # Run Unstructured partition_image on the in-memory image bytes.
                # We request hi_res layout to improve detection of tables/structured content.
                elements = partition_image(
                    file_content=blob,
                    strategy="hi_res",
                    ocr_strategy="ocr_only"
                )

                for el in elements:
                    cat = getattr(el, "category", "text").lower()
                    text = str(el).strip()
                    if not text:
                        continue

                    # Normalize categories -> use 'table' and 'text'; mark image-derived text specially
                    if cat in ("table", "tabular"):
                        block_type = "table"
                    else:
                        # use 'image_text' to indicate origin from image OCR
                        block_type = "image_text"

                    ocr_blocks.append({
                        "type": block_type,
                        "text": text,
                        "metadata": {"source": "docx-image-ocr", "image_index": img_idx}
                    })

            except Exception as e:
                logger.warning(f"OCR failed for DOCX image {img_idx}: {e}")
                # continue with other images

        return ocr_blocks

    def _ocr_full_doc(self, content: bytes) -> List[Dict[str, Any]]:
        """Fallback: run full-document OCR via partition_docx (in-memory)."""
        try:
            elements = partition_docx(file=io.BytesIO(content), strategy="hi_res")
            results: List[Dict[str, Any]] = []
            for el in elements:
                cat = getattr(el, "category", "text").lower()
                text = str(el).strip()
                if not text:
                    continue
                if cat in ("table", "tabular"):
                    btype = "table"
                else:
                    btype = "text"
                results.append({
                    "type": btype,
                    "text": text,
                    "metadata": {"source": "unstructured-ocr"}
                })
            return results
        except Exception as e:
            raise KnowledgeManagementException(
                f"Full OCR extraction failed on DOCX: {e}",
                None,
                "HybridDocxParser"
            )

    def parse(self, content: bytes) -> List[Dict[str, Any]]:
        try:
            doc = docx.Document(io.BytesIO(content))

            # Step 1: Native extraction of paragraphs
            text_blocks = self._extract_text_paragraphs(doc)

            # Step 2: Extract image blobs (no temp files)
            image_blobs = self._extract_image_blobs(doc)

            results: List[Dict[str, Any]] = text_blocks.copy()

            # Step 3: OCR only the images (if enabled)
            if self.enable_ocr and image_blobs:
                logger.info(f"OCRing {len(image_blobs)} embedded images in DOCX")
                image_ocr_blocks = self._ocr_images_only(image_blobs)
                results.extend(image_ocr_blocks)

            # If no images or OCR disabled, we still append image placeholders for traceability
            elif image_blobs:
                for img in image_blobs:
                    results.append({
                        "type": "image",
                        "text": "",
                        "metadata": {"source": "docx-image", "image_index": img.get("image_index")}
                    })

            # Step 4: Fallback to full-document OCR if native text is below threshold
            total_text_len = sum(len(b["text"]) for b in text_blocks)
            if total_text_len < self.text_threshold and self.enable_ocr:
                logger.info("Low native text in DOCX detected — running full-document OCR fallback")
                full_ocr_blocks = self._ocr_full_doc(content)
                # Avoid adding duplicate blocks: naive deduplication by exact text match
                existing_texts = {b["text"] for b in results if b.get("text")}
                for fb in full_ocr_blocks:
                    if fb["text"] not in existing_texts:
                        results.append(fb)

            return results

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse DOCX: {e}",
                None,
                "HybridDocxParser"
            )
