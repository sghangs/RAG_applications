# indexing/sparse_index.py
from typing import List, Dict, Any
from utils.logger import logger

class SparseIndex:
    def __init__(self, index_name: str = "docs"):
        # Replace with OpenSearch/Elasticsearch client
        self.index_name = index_name
        self._local_index = {}  # {chunk_id: doc}

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        for c in chunks:
            cid = c["id"]
            doc = {"text": c["text"], "metadata": c.get("metadata", {})}
            self._local_index[cid] = doc
        logger.info(f"[SparseIndex] indexed {len(chunks)} chunks to {self.index_name}")

    def delete_chunks(self, chunk_ids: List[str]):
        removed = 0
        for cid in chunk_ids:
            if cid in self._local_index:
                del self._local_index[cid]
                removed += 1
        logger.info(f"[SparseIndex] deleted {removed}/{len(chunk_ids)} chunks from {self.index_name}")
