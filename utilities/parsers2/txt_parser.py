from exceptions import KnowledgeManagementException


class HybridTXTParser:
    """
    TXT parser:
    - Splits raw text by lines
    - No OCR logic needed
    """

    def parse(self, content: bytes) -> list[dict]:
        try:
            text = content.decode("utf-8", errors="ignore")
            lines = text.splitlines()
            return [
                {"text": line.strip(), "metadata": {"line": idx, "source": "txt-native"}}
                for idx, line in enumerate(lines, start=1) if line.strip()
            ]
        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse TXT: {e}",
                None,
                "HybridTXTParser"
            )
