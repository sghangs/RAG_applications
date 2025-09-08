import os
import magic
from .hybrid_pdf_parser import HybridPDFParser
from .hybrid_docx_parser import HybridDocxParser
from .hybrid_pptx_parser import HybridPPTXParser
from .hybrid_excel_parser import HybridExcelParser
from .hybrid_csv_parser import HybridCSVParser
from .hybrid_txt_parser import HybridTXTParser
from preprocessing.cleaner import TextCleaner
from utils.config_loader import ConfigLoader
from utils.logger import logger
from exceptions import KnowledgeManagementException


class ParserFactory:
    """
    Factory to select the right parser (by extension or MIME type)
    and apply preprocessing as defined in config.
    """

    _config = ConfigLoader()

    _mime_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/plain": ".txt",
        "text/csv": ".csv",
    }

    _parsers = {
        ".pdf": lambda cfg: HybridPDFParser(
            text_threshold=cfg.get("pdf", "text_threshold", 100),
            enable_ocr=cfg.get("pdf", "enable_ocr", True),
        ),
        ".docx": lambda cfg: HybridDocxParser(
            text_threshold=cfg.get("docx", "text_threshold", 30),
            enable_ocr_images=cfg.get("docx", "enable_ocr_images", True),
        ),
        ".pptx": lambda cfg: HybridPPTXParser(
            text_threshold=cfg.get("pptx", "text_threshold", 50),
            enable_ocr_images=cfg.get("pptx", "enable_ocr_images", True),
        ),
        ".xlsx": lambda cfg: HybridExcelParser(),
        ".xls": lambda cfg: HybridExcelParser(),
        ".csv": lambda cfg: HybridCSVParser(),
        ".txt": lambda cfg: HybridTXTParser(),
    }

    @classmethod
    def _detect_extension(cls, filename: str, content: bytes) -> str:
        # First check actual extension
        ext = os.path.splitext(filename)[-1].lower()
        if ext in cls._parsers:
            return ext

        # Fallback to MIME detection
        try:
            mime = magic.Magic(mime=True).from_buffer(content)
            detected_ext = cls._mime_map.get(mime)
            if detected_ext:
                logger.info(f"Detected MIME {mime}, mapped to {detected_ext}")
                return detected_ext
        except Exception as e:
            logger.warning(f"MIME type detection failed: {e}")

        raise KnowledgeManagementException(
            f"Unsupported file type for {filename}",
            None,
            "ParserFactory"
        )

    @classmethod
    def parse_and_clean(cls, filename: str, content: bytes) -> list[dict]:
        ext = cls._detect_extension(filename, content)
        parser_builder = cls._parsers.get(ext)

        if not parser_builder:
            raise KnowledgeManagementException(
                f"No parser available for extension: {ext}",
                None,
                "ParserFactory"
            )

        parser = parser_builder(cls._config)
        logger.info(f"Selected parser {parser.__class__.__name__} for {filename}")

        blocks = parser.parse(content)

        preprocessing_cfg = cls._config.get(ext.strip("."), "preprocessing", {})
        if preprocessing_cfg:
            cleaner = TextCleaner(preprocessing_cfg)
            blocks = cleaner.clean(blocks)
            logger.info(f"Applied preprocessing for {filename}: {preprocessing_cfg}")

        return blocks
