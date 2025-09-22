# ingestion/parsers/excel_parser.py
import io
import pandas as pd
from typing import List, Dict
from utils.logger import logger
from exceptions import KnowledgeManagementException
from ingestion.parsers.csv_utils import determine_column_types, create_embedding_chunks

class HybridExcelParser:
    """
    Hybrid Excel parser:
    - Reads all sheets in the Excel file
    - Uses column type detection to split text vs metadata
    - Creates embedding-ready chunks
    - Adds sheet name in metadata
    """
    def __init__(self, max_text_length: int = 500, slide_window: int = 1):
        self.max_text_length = max_text_length
        self.slide_window = slide_window

    def parse(self, content: bytes) -> List[Dict]:
        all_chunks = []
        try:
            # Read all sheets into a dict of DataFrames
            sheets: Dict[str, pd.DataFrame] = pd.read_excel(io.BytesIO(content), sheet_name=None)

            for sheet_name, df in sheets.items():
                if df.empty:
                    continue

                text_cols, meta_cols = determine_column_types(df)
                chunks = create_embedding_chunks(df, text_cols, meta_cols,
                                                 max_text_length=self.max_text_length,
                                                 slide_window=self.slide_window)
                # Add sheet name in metadata
                for ch in chunks:
                    ch['metadata']['sheet'] = sheet_name

                all_chunks.extend(chunks)


            return all_chunks

        except Exception as e:
            logger.exception(f"Failed to parse Excel file: {e}")
            raise KnowledgeManagementException(
                f"Failed to parse Excel: {e}",
                None,
                "HybridExcelParser",
            )
