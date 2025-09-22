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
    - Deduplicates overlapping table text from PyMuPDF output
    """

    def __init__(self, text_threshold: int = 100, enable_ocr: bool = True):
        self.text_threshold = text_threshold
        self.enable_ocr = enable_ocr

    def _extract_with_pymupdf(self, page) -> list[tuple]:
        """Return list of (bbox, text) blocks from PyMuPDF."""
        return page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no,...)

    def _extract_with_pdfplumber(self, pdf_path: str, page_num: int) -> tuple[list[str], list[tuple]]:
        """
        Extract tables with pdfplumber.
        Returns: (table_texts, table_bboxes)
        """
        tables_text, table_bboxes = [], []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num]
                tables = page.find_tables()
                for table in tables:
                    table_bboxes.append(table.bbox)
                    data = table.extract()
                    if not data:
                        continue
                    rows = ["\t".join(cell or "" for cell in row) for row in data if row]
                    tables_text.append("\n".join(rows))
        except Exception as e:
            logger.warning(f"pdfplumber failed on page {page_num+1}: {e}")
        return tables_text, table_bboxes

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
                return [
                    {"text": str(el), "metadata": {"page": page_num + 1, "source": "unstructured-ocr"}}
                    for el in elements
                ]
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
                # Step 1: extract raw blocks from PyMuPDF
                pymupdf_blocks = self._extract_with_pymupdf(page)
                raw_text_blocks = [
                    (bbox, txt)
                    for (x0, y0, x1, y1, txt, *_)
                    in pymupdf_blocks
                    if txt and txt.strip()
                    for bbox in [(x0, y0, x1, y1)]
                ]
                raw_text = " ".join(txt for _, txt in raw_text_blocks)

                if len(raw_text.strip()) > self.text_threshold:
                    # Step 2: extract tables with pdfplumber
                    tables_text, table_bboxes = self._extract_with_pdfplumber(tmp_path, page_num)

                    # Step 3: filter PyMuPDF blocks that overlap with table bboxes
                    filtered_texts = []
                    for (x0, y0, x1, y1), txt in raw_text_blocks:
                        overlaps = any(
                            (x0 < tbx1 and x1 > tbx0 and y0 < tby1 and y1 > tby0)
                            for (tbx0, tby0, tbx1, tby1) in table_bboxes
                        )
                        if not overlaps:
                            filtered_texts.append(txt)

                    combined_text = "\n".join(filtered_texts)
                    if tables_text:
                        combined_text += "\n" + "\n\n".join(tables_text)

                    results.append({
                        "text": combined_text.strip(),
                        "metadata": {"page": page_num + 1, "source": "pymupdf+pdfplumber"}
                    })

                else:
                    # OCR fallback
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
