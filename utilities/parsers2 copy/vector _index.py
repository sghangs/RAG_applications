# ingestion/indexing/vector_index.py
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

class VectorIndex:
    def __init__(self, host="localhost", port=6333, collection="documents"):
        # create client
        self.client = QdrantClient(host=host, port=port)
        self.collection = collection
        # note: ensure collection exists in your deployment, create if required

    def upsert_points(self, points: List[Dict[str, Any]]):
        """
        points: list of {id: str, vector: List[float], payload: dict}
        """
        point_structs = [PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points]
        self.client.upsert(collection_name=self.collection, points=point_structs)

    def delete_points(self, point_ids: List[str]):
        if not point_ids:
            return
        self.client.delete(collection_name=self.collection, points_selector={"ids": point_ids})