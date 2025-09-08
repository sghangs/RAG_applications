import os
import magic  # python-magic
from .hybrid_pdf_parser import HybridPDFParser
from .hybrid_docx_parser import HybridDocxParser
from .hybrid_pptx_parser import HybridPPTXParser
from .hybrid_excel_parser import HybridExcelParser
from .hybrid_csv_parser import HybridCSVParser
from .hybrid_txt_parser import HybridTXTParser


class ParserFactory:
    """
    Factory to select the right parser based on file extension or MIME type.
    Priority:
      1. Detect via MIME type (content sniffing).
      2. Fall back to file extension if MIME detection fails.
    """

    # MIME type to parser mapping
    _mime_parsers = {
        "application/pdf": lambda: HybridPDFParser(enable_ocr=True),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": lambda: HybridDocxParser(enable_ocr_images=True),
        "application/msword": lambda: HybridDocxParser(enable_ocr_images=True),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": lambda: HybridPPTXParser(enable_ocr_images=True),
        "application/vnd.ms-powerpoint": lambda: HybridPPTXParser(enable_ocr_images=True),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": lambda: HybridExcelParser(),
        "application/vnd.ms-excel": lambda: HybridExcelParser(),
        "text/csv": lambda: HybridCSVParser(),
        "text/plain": lambda: HybridTXTParser(),
    }

    # Extension fallback
    _ext_parsers = {
        ".pdf": lambda: HybridPDFParser(enable_ocr=True),
        ".docx": lambda: HybridDocxParser(enable_ocr_images=True),
        ".doc": lambda: HybridDocxParser(enable_ocr_images=True),
        ".pptx": lambda: HybridPPTXParser(enable_ocr_images=True),
        ".ppt": lambda: HybridPPTXParser(enable_ocr_images=True),
        ".xlsx": lambda: HybridExcelParser(),
        ".xls": lambda: HybridExcelParser(),
        ".csv": lambda: HybridCSVParser(),
        ".txt": lambda: HybridTXTParser(),
    }

    @classmethod
    def get_parser(cls, filename: str, content: bytes):
        # 1. Try MIME type detection
        try:
            mime = magic.Magic(mime=True).from_buffer(content[:4096])
            parser_builder = cls._mime_parsers.get(mime)
            if parser_builder:
                return parser_builder()
        except Exception:
            pass

        # 2. Fall back to file extension
        ext = os.path.splitext(filename)[-1].lower()
        parser_builder = cls._ext_parsers.get(ext)
        if parser_builder:
            return parser_builder()

        raise ValueError(f"No parser available for file: {filename}")
