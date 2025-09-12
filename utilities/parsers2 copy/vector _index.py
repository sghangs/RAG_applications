import qdrant_client
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

class VectorIndex:
    def __init__(self, collection="documents"):
        self.client = qdrant_client.QdrantClient(host="localhost", port=6333)
        self.collection = collection

    def upsert(self, embeddings, chunks, doc_id: str):
        points = [
            PointStruct(
                id=f"{doc_id}-{i}",
                vector=emb,
                payload={"text": c["text"], "metadata": {**c["metadata"], "doc_id": doc_id}}
            )
            for i, (emb, c) in enumerate(zip(embeddings, chunks))
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def delete(self, doc_id: str):
        self.client.delete(
            collection_name=self.collection,
            points_selector={"filter": Filter(
                must=[FieldCondition(key="metadata.doc_id", match=MatchValue(value=doc_id))]
            )}
        )
