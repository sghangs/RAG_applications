import pandas as pd
from typing import List, Dict

def determine_column_types(df: pd.DataFrame):
    """
    Determine which columns should go into embedding text vs metadata.
    Numeric/categorical → metadata
    Text/object → embedding
    """
    text_cols, meta_cols = [], []
    for col, dtype in df.dtypes.items():
        if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
            text_cols.append(col)
        else:
            meta_cols.append(col)
    return text_cols, meta_cols


def create_embedding_chunks(
    df: pd.DataFrame,
    text_cols: List[str],
    meta_cols: List[str],
    max_text_length: int = 500,
    slide_window: int = 1
) -> List[Dict]:
    """
    Create chunks for embedding:
    - Combines multiple rows until max_text_length reached
    - Keeps metadata for each row
    """
    chunks = []
    current_texts = []
    current_meta = []

    for idx in range(len(df)):
        row = df.iloc[idx]
        text_content = " ".join([str(row[col]) for col in text_cols if pd.notna(row[col])]).strip()
        row_meta = {col: row[col] for col in meta_cols}

        if not text_content:
            text_content = " "

        current_texts.append(text_content)
        current_meta.append(row_meta)

        combined_text = " ".join(current_texts)
        if len(combined_text.strip()) >= max_text_length or idx == len(df) - 1:
            chunks.append({
                "text": combined_text,
                "metadata": {"rows": current_meta}
            })
            # Slide window
            current_texts = current_texts[slide_window:]
            current_meta = current_meta[slide_window:]

    return chunks
