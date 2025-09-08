import pandas as pd
import io
from exceptions import KnowledgeManagementException


class HybridCSVParser:
    """
    Hybrid CSV parser:
    - Straightforward row-based parsing using pandas
    - No OCR fallback needed
    """

    def parse(self, content: bytes) -> list[dict]:
        blocks = []
        try:
            df = pd.read_csv(io.BytesIO(content))
            for idx, row in df.iterrows():
                text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
                blocks.append({
                    "text": text,
                    "metadata": {"row": idx, "source": "csv-native"}
                })
            return blocks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse CSV: {e}",
                None,
                "HybridCSVParser"
            )
