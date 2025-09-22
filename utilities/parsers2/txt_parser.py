# ingestion/parsers/txt_parser.py
from exceptions import KnowledgeManagementException
from typing import List, Dict

class HybridTXTParser:
    """
    Optimized TXT parser:
    - Splits text by lines or paragraphs intelligently
    - Filters empty lines
    - Preserves line numbers for metadata
    - Optional chunking for embeddings to reduce small-text noise
    """
    def __init__(self, chunk_size: int = 500, slide_window: int = 1):
        """
        chunk_size: approximate number of characters per chunk
        slide_window: overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.slide_window = slide_window

    def parse(self, content: bytes) -> List[Dict]:
        try:
            text = content.decode("utf-8", errors="ignore").replace("\r\n", "\n")
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            # Step 1: Create basic line-level blocks
            line_blocks = [
                {"text": line, "metadata": {"line": idx, "source": "txt-native"}}
                for idx, line in enumerate(lines, start=1)
            ]

            # Step 2: Chunk small lines into larger embedding-ready blocks
            chunks = []
            current_texts = []
            current_meta = []

            for block in line_blocks:
                current_texts.append(block["text"])
                current_meta.append(block["metadata"])

                combined_text = " ".join(current_texts)
                if len(combined_text) >= self.chunk_size:
                    chunks.append({
                        "text": combined_text,
                        "metadata": {"lines": current_meta}
                    })
                    # Slide window
                    current_texts = current_texts[self.slide_window:]
                    current_meta = current_meta[self.slide_window:]

            # Add any remaining lines
            if current_texts:
                chunks.append({
                    "text": " ".join(current_texts),
                    "metadata": {"lines": current_meta}
                })

            return chunks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse TXT: {e}",
                None,
                "HybridTXTParser"
            )

