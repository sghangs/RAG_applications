from .base import BaseParser

class HybridTXTParser(BaseParser):
    def parse(self, content: bytes) -> list[dict]:
        text = content.decode("utf-8", errors="ignore")
        blocks = []
        for idx, line in enumerate(text.splitlines(), start=1):
            if line.strip():
                blocks.append({"text": line.strip(), "metadata": {"source": "txt", "line": idx}})
        return blocks
