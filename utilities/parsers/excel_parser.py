import io
import pandas as pd
from unstructured.partition.xlsx import partition_xlsx
from unstructured.partition.xls import partition_xls
from .base import BaseParser

class HybridExcelParser(BaseParser):
    def _parse_with_unstructured(self, content: bytes, ext: str) -> list[dict]:
        if ext.lower() == "xlsx":
            elements = partition_xlsx(file=io.BytesIO(content))
        else:
            elements = partition_xls(file=io.BytesIO(content))
        blocks = []
        for idx, el in enumerate(elements, start=1):
            text = str(el).strip()
            if text:
                blocks.append({"text": text, "metadata": {"source": f"unstructured-{ext}", "block": idx}})
        return blocks

    def _parse_with_pandas(self, content: bytes) -> list[dict]:
        blocks = []
        xl = pd.ExcelFile(io.BytesIO(content))
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            for idx, row in df.iterrows():
                text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
                if str(text).strip():
                    blocks.append({
                        "text": text,
                        "metadata": {"source": "pandas-excel", "sheet": sheet, "row": idx}
                    })
        return blocks

    def parse(self, content: bytes, ext: str = "xlsx") -> list[dict]:
        try:
            blocks = self._parse_with_unstructured(content, ext)
            if blocks:
                return blocks
        except Exception:
            pass
        return self._parse_with_pandas(content)
