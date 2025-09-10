# indexing/vector_index.py
from typing import List, Dict, Any
from utils.logger import logger

class VectorIndex:
    def __init__(self, collection: str = "documents"):
        # Replace with qdrant_client.QdrantClient or other vector DB client
        # self.client = QdrantClient(...)
        self.collection = collection
        self._local_store = {}  # example in-memory store: {point_id: payload}

    def upsert(self, embeddings: List[List[float]], chunks: List[Dict[str, Any]]):
        # embeddings and chunks are aligned lists
        for emb, chunk in zip(embeddings, chunks):
            pid = chunk["id"]
            payload = {"text": chunk["text"], "metadata": chunk.get("metadata", {})}
            # TODO: call vector DB upsert
            self._local_store[pid] = {"vector": emb, "payload": payload}
        logger.info(f"[VectorIndex] upserted {len(chunks)} vectors to {self.collection}")

    def delete_points(self, point_ids: List[str]):
        # TODO: call vector DB delete API (by point ids)
        removed = 0
        for pid in point_ids:
            if pid in self._local_store:
                del self._local_store[pid]
                removed += 1
        logger.info(f"[VectorIndex] deleted {removed}/{len(point_ids)} points from {self.collection}")
