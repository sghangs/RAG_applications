import fitz  # PyMuPDF
import pdfplumber
import tempfile
import os
from unstructured.partition.pdf import partition_pdf
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridPDFParser:
    """
    Hybrid PDF parser:
    - Uses PyMuPDF for fast text extraction
    - Uses pdfplumber for improved table parsing
    - Falls back to Unstructured OCR if page has little/no text
    """

    def __init__(self, text_threshold: int = 100, enable_ocr: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr = enable_ocr

    def _extract_with_pymupdf(self, page) -> str:
        return page.get_text("text")

    def _extract_with_pdfplumber(self, pdf_path: str, page_num: int) -> str:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num]
                tables = page.extract_tables()
                if not tables:
                    return ""
                text_blocks = []
                for table in tables:
                    rows = ["\t".join(row) for row in table if row]
                    text_blocks.append("\n".join(rows))
                return "\n".join(text_blocks)
        except Exception as e:
            logger.warning(f"pdfplumber failed on page {page_num+1}: {e}")
            return ""

    def _extract_with_ocr(self, doc, page_num: int) -> list[dict]:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                writer = fitz.open()
                writer.insert_pdf(doc, from_page=page_num, to_page=page_num)
                writer.save(tmp.name)
                writer.close()
                elements = partition_pdf(
                    filename=tmp.name,
                    strategy="hi_res",
                    ocr_strategy="ocr_only",
                )
                os.unlink(tmp.name)
                return [{"text": str(el), "metadata": {"page": page_num + 1, "source": "unstructured-ocr"}} for el in elements]
        except Exception as e:
            raise KnowledgeManagementException(
                f"OCR extraction failed on page {page_num+1}: {e}",
                page_num,
                "HybridPDFParser",
            )

    def parse(self, content: bytes) -> list[dict]:
        results = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")

            # Save content to temp file for pdfplumber
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                tmp_pdf.write(content)
                tmp_pdf.flush()
                tmp_path = tmp_pdf.name

            for page_num, page in enumerate(doc):
                text = self._extract_with_pymupdf(page)

                if len(text.strip()) > self.text_threshold:
                    # Native text extraction
                    tables_text = self._extract_with_pdfplumber(tmp_path, page_num)
                    combined_text = text + ("\n" + tables_text if tables_text else "")
                    results.append({
                        "text": combined_text.strip(),
                        "metadata": {"page": page_num + 1, "source": "pymupdf/pdfplumber"}
                    })
                else:
                    if self.enable_ocr:
                        ocr_blocks = self._extract_with_ocr(doc, page_num)
                        results.extend(ocr_blocks)
                    else:
                        logger.warning(f"Page {page_num+1} skipped (low text, OCR disabled)")

            os.unlink(tmp_path)
            return results

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse PDF: {e}",
                None,
                "HybridPDFParser"
            )
