from opensearchpy import OpenSearch

class SparseIndex:
    def __init__(self, index="docs"):
        self.client = OpenSearch(["http://localhost:9200"])
        self.index = index

    def index_chunks(self, chunks, doc_id: str):
        for i, c in enumerate(chunks):
            body = {
                "text": c["text"],
                "metadata": {**c["metadata"], "doc_id": doc_id}
            }
            self.client.index(index=self.index, id=f"{doc_id}-{i}", body=body)

    def delete(self, doc_id: str):
        self.client.delete_by_query(
            index=self.index,
            body={"query": {"term": {"metadata.doc_id": doc_id}}}
        )
