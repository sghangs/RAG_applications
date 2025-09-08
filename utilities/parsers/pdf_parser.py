import io
import fitz  # PyMuPDF
import pdfplumber
from unstructured.partition.pdf import partition_pdf
from .base import BaseParser


class HybridPDFParser(BaseParser):
    def __init__(self, ocr_threshold_chars: int = 50, sample_pages: int = 3):
        """
        :param ocr_threshold_chars: If extracted chars < threshold, assume scanned PDF.
        :param sample_pages: Number of pages to check for text before deciding OCR.
        """
        self.ocr_threshold_chars = ocr_threshold_chars
        self.sample_pages = sample_pages

    def _is_scanned_pdf(self, pdf_bytes: bytes) -> bool:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for i, page in enumerate(doc, start=1):
            if i > self.sample_pages:
                break
            text = page.get_text("text")
            if len(text.strip()) > self.ocr_threshold_chars:
                return False
        return True

    def _parse_with_unstructured(self, pdf_bytes: bytes, use_ocr: bool) -> list[dict]:
        strategy = "hi_res" if use_ocr else "fast"
        elements = partition_pdf(
            file=io.BytesIO(pdf_bytes),
            strategy=strategy,
            infer_table_structure=True
        )
        blocks = []
        for idx, el in enumerate(elements, start=1):
            text = str(el).strip()
            if text:
                blocks.append({
                    "text": text,
                    "metadata": {"source": f"unstructured-{strategy}", "block": idx}
                })
        return blocks

    def _parse_with_pdfplumber(self, pdf_bytes: bytes) -> list[dict]:
        blocks = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Text
                text = page.extract_text()
                if text:
                    blocks.append({"text": text, "metadata": {"source": "pdfplumber", "page": page_num}})

                # Tables
                for t_idx, table in enumerate(page.extract_tables(), start=1):
                    table_text = "\n".join([", ".join(row) for row in table if row])
                    if table_text.strip():
                        blocks.append({
                            "text": table_text,
                            "metadata": {"source": "pdfplumber-table", "page": page_num, "table": t_idx}
                        })
        return blocks

    def _parse_with_pymupdf(self, pdf_bytes: bytes) -> list[dict]:
        blocks = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                blocks.append({"text": text, "metadata": {"source": "pymupdf", "page": page_num}})
        return blocks

    def parse(self, content: bytes) -> list[dict]:
        # Step 1: Detect scanned
        scanned = self._is_scanned_pdf(content)

        # Step 2: Run Unstructured (OCR if scanned)
        blocks = self._parse_with_unstructured(content, use_ocr=scanned)

        # Step 3: Check if tables exist
        table_blocks = [b for b in blocks if "table" in b["metadata"].get("source", "").lower()]
        if len(table_blocks) == 0:
            print("⚠️ No tables detected → running PDFPlumber for better table extraction...")
            blocks.extend(self._parse_with_pdfplumber(content))

        # Step 4: If still empty → fallback to PyMuPDF
        if len(blocks) == 0:
            print("⚠️ Unstructured & PDFPlumber failed → fallback to PyMuPDF...")
            blocks = self._parse_with_pymupdf(content)

        return blocks
