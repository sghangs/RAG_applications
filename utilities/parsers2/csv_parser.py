import pandas as pd
import io
from typing import List, Dict
from exceptions import KnowledgeManagementException
from utils.logger import logger
from utils.csv_utils import determine_column_types, create_embedding_chunks


class HybridCSVParser:
    """
    Hybrid CSV parser:
    - Separates text columns for embeddings and metadata columns for filtering
    - Creates chunks using sliding window approach to optimize embeddings
    - Includes fallback for rows/chunks with no text
    """

    def __init__(self, max_text_length: int = 500, slide_window: int = 1, fallback_text: str = "N/A"):
        self.max_text_length = max_text_length
        self.slide_window = slide_window
        self.fallback_text = fallback_text

    def parse(self, content: bytes) -> List[Dict]:
        try:
            df = pd.read_csv(io.BytesIO(content))
            if df.empty:
                logger.warning("CSV file is empty")
                return []

            text_cols, meta_cols = determine_column_types(df)
            chunks = create_embedding_chunks(
                df,
                text_cols,
                meta_cols,
                max_text_length=self.max_text_length,
                slide_window=self.slide_window
            )

            # Fallback: ensure chunks with no text get a placeholder
            for chunk in chunks:
                if not chunk["text"].strip():
                    chunk["text"] = self.fallback_text

            return chunks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse CSV: {e}",
                None,
                "HybridCSVParser"
            )
