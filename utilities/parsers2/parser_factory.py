import os
from .hybrid_pdf_parser import HybridPDFParser
from .hybrid_docx_parser import HybridDocxParser
from .hybrid_pptx_parser import HybridPPTXParser
from .hybrid_excel_parser import HybridExcelParser
from .hybrid_csv_parser import HybridCSVParser
from .hybrid_txt_parser import HybridTXTParser
from preprocessing.cleaner import TextCleaner
from utils.config_loader import ConfigLoader
from utils.logger import logger

class ParserFactory:
    """
    Factory to select the right parser and apply preprocessing
    """

    _config = ConfigLoader()

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
    def parse_and_clean(cls, filename: str, content: bytes) -> list[dict]:
        ext = os.path.splitext(filename)[-1].lower()
        parser_builder = cls._parsers.get(ext)

        if not parser_builder:
            raise ValueError(f"No parser available for extension: {ext}")

        parser = parser_builder(cls._config)
        logger.info(f"Selected parser {parser.__class__.__name__} for {filename}")

        blocks = parser.parse(content)

        # Apply preprocessing if config exists
        preprocessing_cfg = cls._config.get(ext.strip("."), "preprocessing", {})
        if preprocessing_cfg:
            cleaner = TextCleaner(preprocessing_cfg)
            blocks = cleaner.clean(blocks)
            logger.info(f"Applied preprocessing for {filename}: {preprocessing_cfg}")

        return blocks
