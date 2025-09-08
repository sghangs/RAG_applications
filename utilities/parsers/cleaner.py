import re
import html
import unicodedata
from utils.logger import logger


class TextCleaner:
    def __init__(self, remove_html: bool = True, normalize_unicode: bool = True,
                 remove_boilerplate: bool = True, collapse_whitespace: bool = True):
        self.remove_html = remove_html
        self.normalize_unicode = normalize_unicode
        self.remove_boilerplate = remove_boilerplate
        self.collapse_whitespace = collapse_whitespace

    def clean_block(self, block: dict) -> dict:
        """Clean a single block {text, metadata}"""
        text = block.get("text", "")

        # Decode HTML entities
        if self.remove_html:
            text = html.unescape(text)

        # Strip HTML tags (basic heuristic)
        if self.remove_html:
            text = re.sub(r"<[^>]+>", " ", text)

        # Unicode normalization
        if self.normalize_unicode:
            text = unicodedata.normalize("NFKC", text)

        # Remove boilerplate patterns (page numbers, repeated headers, etc.)
        if self.remove_boilerplate:
            text = re.sub(r"Page\s+\d+(\s+of\s+\d+)?", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"Confidential|Draft|CompanyName", " ", text, flags=re.IGNORECASE)

        # Collapse multiple spaces/newlines
        if self.collapse_whitespace:
            text = re.sub(r"\s+", " ", text).strip()

        cleaned_block = {"text": text, "metadata": block.get("metadata", {})}

        return cleaned_block

    def clean_blocks(self, blocks: list[dict]) -> list[dict]:
        logger.info(f"Cleaning {len(blocks)} blocks")
        return [self.clean_block(block) for block in blocks if block.get("text")]
