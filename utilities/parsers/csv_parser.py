import io
import pandas as pd
from .base import BaseParser

class HybridCSVParser(BaseParser):
    def parse(self, content: bytes) -> list[dict]:
        df = pd.read_csv(io.BytesIO(content))
        blocks = []
        for idx, row in df.iterrows():
            text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
            if str(text).strip():
                blocks.append({
                    "text": text,
                    "metadata": {"source": "pandas-csv", "row": idx}
                })
        return blocks
