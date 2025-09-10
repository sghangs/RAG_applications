# indexing/metadata_store.py
from typing import Optional, Dict, Any
from exceptions import KnowledgeManagementException
from utils.logger import logger

# NOTE: this file uses an in-memory store for example.
# Replace with a real DB/ORM (Postgres + SQLAlchemy) in production.

class MetadataStore:
    def __init__(self):
        # schema:
        # docs[doc_id] = {
        #   "title": str,
        #   "uri": str,
        #   "checksum": str,
        #   "project": str,
        #   "chunks": {chunk_id: checksum, ...}
        #   "deleted": bool,
        #   "updated_at": timestamp (optional)
        # }
        self.docs: Dict[str, Dict[str, Any]] = {}

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.docs.get(doc_id)

    def upsert_document(self, doc_id: str, title: str, uri: str, checksum: str, project: str, chunks: list):
        try:
            chunk_map = {c["id"]: c["checksum"] for c in chunks}
            self.docs[doc_id] = {
                "title": title,
                "uri": uri,
                "checksum": checksum,
                "project": project,
                "chunks": chunk_map,
                "deleted": False
            }
            logger.info(f"[MetadataStore] upserted doc {doc_id} ({len(chunk_map)} chunks)")
        except Exception as e:
            raise KnowledgeManagementException(f"Failed to upsert metadata: {e}", doc_id, "MetadataStore")

    def get_chunks(self, doc_id: str) -> Dict[str, str]:
        doc = self.docs.get(doc_id)
        return doc.get("chunks", {}) if doc else {}

    def remove_chunks(self, doc_id: str, chunk_ids: list):
        doc = self.docs.get(doc_id)
        if not doc:
            return
        for cid in chunk_ids:
            doc["chunks"].pop(cid, None)
        logger.info(f"[MetadataStore] removed {len(chunk_ids)} chunks from {doc_id}")

    def delete_document(self, doc_id: str):
        """Mark as deleted and remove metadata"""
        if doc_id in self.docs:
            # Optionally keep audit trail: set deleted flag + timestamp
            self.docs[doc_id]["deleted"] = True
            # remove chunk map
            self.docs[doc_id]["chunks"] = {}
            logger.info(f"[MetadataStore] marked document deleted: {doc_id}")
        else:
            logger.warning(f"[MetadataStore] delete called for unknown doc: {doc_id}")
