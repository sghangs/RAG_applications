# ingestion/pipeline.py
import hashlib
import uuid
import requests
from typing import List, Dict, Any
from ingestion.parsers.parser_factory import ParserFactory
from ingestion.preprocessing.cleaner import TextCleaner
from ingestion.chunking.smart_chunker import SmartChunker
from ingestion.embedding.embedder import Embedder
from ingestion.indexing.vector_index import VectorIndex
from ingestion.indexing.sparse_index import SparseIndex
from ingestion.indexing.metadata_store import MetadataStore
from ingestion.utils.logger import logger
from ingestion.utils.exceptions import KnowledgeManagementException

def chunk_text_hash(text: str) -> str:
    """Return sha256 hex of canonicalized chunk text."""
    # canonicalize: normalize whitespace (more normalization can be added)
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def chunk_point_id_from_hash(chunk_hash: str) -> str:
    """Deterministic UUIDv5 id derived from chunk hash (stable across runs)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_hash))


class IngestionPipeline:
    def __init__(self):
        self.cleaner = TextCleaner()            # should canonicalize text consistently
        self.chunker = SmartChunker()           # deterministic chunking
        self.embedder = Embedder()
        self.vector_index = VectorIndex()
        self.sparse_index = SparseIndex()
        self.metadata_store = MetadataStore()   # must support per-chunk persistence

    def ingest_file(self, doc_id: str, content: bytes, filename: str, project: str = "KB"):
        """
        doc_id: stable id from SharePoint (item id) or path
        content: raw bytes
        """
        try:
            # 1. Parse
            parser = ParserFactory.get_parser(filename, content)  # adjust signature if needed
            blocks = parser.parse(content)

            # 2. Clean and chunk
            cleaned_blocks = self.cleaner.clean_blocks(blocks)
            chunks = self.chunker.chunk(cleaned_blocks)  # returns list of {"text", "metadata"}

            # 3. Build new chunk-hash map (preserve positions)
            new_chunk_infos: List[Dict[str, Any]] = []
            for pos, c in enumerate(chunks):
                text = c["text"]
                c_hash = chunk_text_hash(text)
                point_id = chunk_point_id_from_hash(c_hash)
                new_chunk_infos.append({
                    "hash": c_hash,
                    "point_id": point_id,
                    "text": text,
                    "pos": pos,
                    "metadata": c.get("metadata", {})
                })

            new_hash_set = {ci["hash"] for ci in new_chunk_infos}

            # 4. Load old chunk hashes for this doc
            old_chunk_hashes = self.metadata_store.get_doc_chunk_hashes(doc_id) or set()

            # 5. Determine diffs
            added_hashes = new_hash_set - old_chunk_hashes
            removed_hashes = old_chunk_hashes - new_hash_set
            unchanged_hashes = new_hash_set & old_chunk_hashes

            logger.info(f"Doc {doc_id}: added={len(added_hashes)}, removed={len(removed_hashes)}, unchanged={len(unchanged_hashes)}")

            # 6. Prepare added chunk objects in deterministic order
            hashes_to_infos = {ci["hash"]: ci for ci in new_chunk_infos}
            added_infos = [hashes_to_infos[h] for h in new_chunk_infos if h["hash"] in added_hashes]  # preserve order

            # 7. Embed added chunks only (batch)
            if added_infos:
                texts = [ci["text"] for ci in added_infos]
                embeddings = self.embedder.embed_batch(texts)
                # upsert to vector DB with stable point ids
                points = []
                for emb, ci in zip(embeddings, added_infos):
                    payload = {
                        "text": ci["text"],
                        "metadata": {
                            **ci["metadata"],
                            "doc_id": doc_id,
                            "pos": ci["pos"],
                            "chunk_hash": ci["hash"]
                        }
                    }
                    points.append({"id": ci["point_id"], "vector": emb, "payload": payload})
                self.vector_index.upsert_points(points)

                # also index in sparse index
                self.sparse_index.index_chunks([
                    {"id": ci["point_id"], "text": ci["text"], "metadata": {"doc_id": doc_id, "pos": ci["pos"], "chunk_hash": ci["hash"]}}
                    for ci in added_infos
                ])

            # 8. Handle removed chunks: delete or update payload to remove doc reference.
            if removed_hashes:
                # find point ids for removed hashes
                removed_point_ids = [chunk_point_id_from_hash(h) for h in removed_hashes]
                # If your system allows shared chunks across docs, you might instead remove only doc reference.
                # Here we delete points completely (if you do not share across docs).
                self.vector_index.delete_points(removed_point_ids)
                self.sparse_index.delete_chunks_by_ids(removed_point_ids)

            # 9. Update metadata: store new set of hashes for doc (and optionally positions)
            # metadata_store should atomically set doc->list_of_hashes and chunk->info mapping
            self.metadata_store.set_doc_chunk_hashes(doc_id, new_hash_set, new_chunk_infos)

            logger.info(f"Ingestion finished for doc {doc_id}")

        except Exception as e:
            logger.exception(f"Error ingesting {doc_id}: {e}")
            raise KnowledgeManagementException(str(e), doc_id, "ingest_file")
