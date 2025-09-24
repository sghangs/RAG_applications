# preprocessor.py
import re
import unicodedata
import hashlib
from collections import Counter
from typing import List, Dict, Optional

import cv2
import numpy as np
from PIL import Image
import io


class Preprocessor:
    """
    Production-grade preprocessing & cleaning for RAG.
    - Universal cleaning (all doc types)
    - Type-specific cleaning (text, table, code, OCR images)
    """

    def __init__(self, enable_dedup: bool = True, min_chunk_len: int = 10):
        self.enable_dedup = enable_dedup
        self.min_chunk_len = min_chunk_len
        self._seen_hashes = set()

    # ---------------------------
    # Universal utilities
    # ---------------------------

    def normalize_text(self, text: str) -> str:
        """Normalize unicode, strip junk, collapse whitespace, dehyphenate."""
        if not text:
            return ""

        # Normalize unicode
        t = unicodedata.normalize("NFKC", text)

        # Dehyphenate across line breaks
        t = re.sub(r"(\w+)-\n(\w+)", r"\1\2", t)

        # Normalize line breaks
        t = re.sub(r"\r\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)

        # Collapse spaces/tabs
        t = re.sub(r"[ \t]+", " ", t)

        # Remove zero-width / control chars
        t = "".join(ch for ch in t if unicodedata.category(ch)[0] != "C" or ch in "\n\t")

        return t.strip()

    def deduplicate(self, text: str) -> bool:
        """Check if text is duplicate based on hash; return True if duplicate."""
        if not text:
            return True
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False

    def remove_headers_footers(self, page_texts: List[str], top_n: int = 3, min_freq: float = 0.5) -> List[str]:
        """Detect repeated header/footer lines across pages and remove them."""
        head_tail = []
        for p in page_texts:
            lines = p.splitlines()
            head_tail.extend(lines[:top_n] + lines[-top_n:])
        counts = Counter(head_tail)
        n_pages = len(page_texts)
        repeated = {line for line, c in counts.items() if c / n_pages >= min_freq}

        cleaned_pages = []
        for p in page_texts:
            lines = [ln for ln in p.splitlines() if ln not in repeated]
            cleaned_pages.append("\n".join(lines))
        return cleaned_pages

    def chunk_hash(self, text: str) -> str:
        """Return deterministic hash for deduplication / point_id generation."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ---------------------------
    # Text blocks
    # ---------------------------

    def clean_text_block(self, block: Dict) -> Optional[Dict]:
        """Clean and normalize a text block (used for PDF/DOCX/PPTX/TXT)."""
        text = self.normalize_text(block.get("text", ""))
        if len(text) < self.min_chunk_len:
            return None
        if self.enable_dedup and self.deduplicate(text):
            return None
        block["text"] = text
        return block

    # ---------------------------
    # Table blocks
    # ---------------------------

    def clean_table_block(self, block: Dict) -> Optional[Dict]:
        """
        Clean table text block.
        - Normalize each row
        - Add column names inline if missing
        """
        text = self.normalize_text(block.get("text", ""))
        if not text:
            return None

        # Heuristic: collapse multiple spaces into single
        lines = [re.sub(r"\s{2,}", " | ", ln.strip()) for ln in text.splitlines() if ln.strip()]
        block["text"] = "\n".join(lines)

        if self.enable_dedup and self.deduplicate(block["text"]):
            return None
        return block

    # ---------------------------
    # Code blocks
    # ---------------------------

    def clean_code_block(self, block: Dict) -> Optional[Dict]:
        """
        Clean code block.
        - Normalize indentation
        - Keep code intact, just strip trailing whitespace
        """
        text = block.get("text", "").rstrip()
        if not text:
            return None
        block["text"] = text
        return block

    # ---------------------------
    # Image preprocessing for OCR
    # ---------------------------

    def preprocess_image_for_ocr(self, img_bytes: bytes) -> bytes:
        """
        Prepare image for OCR:
        - grayscale
        - denoise
        - adaptive threshold
        - deskew (basic)
        """
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        arr = np.array(img)

        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        gray = cv2.medianBlur(gray, 3)
        th = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # TODO: add deskew if needed
        _, buf = cv2.imencode(".png", th)
        return buf.tobytes()

    # ---------------------------
    # Orchestrator
    # ---------------------------

    def preprocess_blocks(self, blocks: List[Dict], remove_headers: bool = True) -> List[Dict]:
        """
        Run appropriate cleaning based on block type.
        Optionally remove headers/footers if document is multi-page.
        """
        cleaned = []

        # If requested, try to remove headers/footers from multi-page docs
        if remove_headers:
            # Collect text by page for detection
            pages = {}
            for b in blocks:
                page = b.get("metadata", {}).get("page")
                if page is not None:
                    pages.setdefault(page, []).append(b.get("text", ""))

            if pages:
                page_texts = ["\n".join(txts) for _, txts in sorted(pages.items())]
                page_texts = self.remove_headers_footers(page_texts)

                # Rewrite cleaned text back into blocks
                flat = []
                for (page, blocks_in_page), new_text in zip(sorted(pages.items()), page_texts):
                    lines = new_text.splitlines()
                    idx = 0
                    for b in blocks_in_page:
                        if idx < len(lines):
                            b["text"] = lines[idx]
                            idx += 1
                        flat.append(b)
                blocks = flat  # overwrite with header/footer-removed version

        # Now run type-based cleaning
        for b in blocks:
            btype = b.get("type", "text")
            if btype == "text":
                out = self.clean_text_block(b)
            elif btype == "table":
                out = self.clean_table_block(b)
            elif btype == "code":
                out = self.clean_code_block(b)
            else:
                out = b  # leave images/unknown types
            if out:
                cleaned.append(out)

        return cleaned
