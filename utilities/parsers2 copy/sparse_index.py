# ingestion/indexing/sparse_index.py
from typing import List, Dict, Any
from opensearchpy import OpenSearch

class SparseIndex:
    def __init__(self, hosts=None, index_name="docs"):
        hosts = hosts or ["http://localhost:9200"]
        self.client = OpenSearch(hosts)
        self.index = index_name

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        # chunks: list of {id, text, metadata}
        for c in chunks:
            self.client.index(index=self.index, id=c["id"], body={"text": c["text"], "metadata": c.get("metadata", {})})

    def delete_chunks_by_ids(self, ids: List[str]):
        if not ids:
            return
        for _id in ids:
            try:
                self.client.delete(index=self.index, id=_id)
            except Exception:
                # ignore missing docs
                pass