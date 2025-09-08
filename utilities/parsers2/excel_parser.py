import pandas as pd
import io
from utils.logger import logger
from exceptions import KnowledgeManagementException


class HybridExcelParser:
    """
    Hybrid Excel parser:
    - Reads structured text/tables via pandas
    - OCR fallback not common (only if cells contain images, rarely used)
    """

    def parse(self, content: bytes) -> list[dict]:
        blocks = []
        try:
            xls = pd.ExcelFile(io.BytesIO(content))
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)
                for idx, row in df.iterrows():
                    text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
                    blocks.append({
                        "text": text,
                        "metadata": {"sheet": sheet_name, "row": idx, "source": "excel-native"}
                    })
            return blocks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Failed to parse Excel: {e}",
                None,
                "HybridExcelParser"
            )
