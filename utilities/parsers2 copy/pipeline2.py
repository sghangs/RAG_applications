# ingestion/pipeline.py
import requests
from typing import List, Dict, Any
from ingestion.parsers.parser_factory import ParserFactory
from ingestion.preprocessing.cleaner import TextCleaner
from ingestion.chunking.stable_chunker import StableChunker
from ingestion.embedding.embedder import Embedder
from ingestion.indexing.vector_index import VectorIndex
from ingestion.indexing.sparse_index import SparseIndex
from ingestion.indexing.metadata_store import MetadataStore
from ingestion.utils.hashing import compute_checksum, chunk_text_hash, point_id_from_chunk_hash
from ingestion.utils.logger import get_logger
from ingestion.utils.exceptions import KnowledgeManagementException

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(self, db_dsn: str):
        self.cleaner = TextCleaner()
        self.chunker = StableChunker()
        self.embedder = Embedder()
        self.vector_index = VectorIndex()
        self.sparse_index = SparseIndex()
        self.metadata = MetadataStore(db_dsn)

    def _download(self, file_url: str) -> bytes:
        r = requests.get(file_url)
        if r.status_code != 200:
            raise KnowledgeManagementException(f"Failed to download {file_url}: {r.status_code}")
        return r.content

    def ingest_from_sharepoint(self, doc_id: str, file_url: str, filename: str, project: str = "KB"):
        try:
            content = self._download(file_url)
            file_checksum = compute_checksum(content)

            old_checksum = self.metadata.get_checksum(doc_id)
            # fetch old hashes set
            old_hashes = self.metadata.get_doc_chunk_hashes(doc_id) or set()

            # parse
            parser = ParserFactory.get_parser(filename, content)
            blocks = parser.parse(content)

            # clean + chunk
            cleaned = self.cleaner.clean_blocks(blocks)
            chunks = self.chunker.chunk(cleaned)

            # build new chunk infos
            new_infos = []
            for pos, c in enumerate(chunks):
                text = c["text"]
                chash = chunk_text_hash(text)
                pid = point_id_from_chunk_hash(chash)
                new_infos.append({"hash": chash, "point_id": pid, "pos": pos, "text": text, "metadata": c.get("metadata", {})})

            new_hashes = {ci["hash"] for ci in new_infos}

            added = new_hashes - old_hashes
            removed = old_hashes - new_hashes
            unchanged = new_hashes & old_hashes

            logger.info(f"Doc {doc_id}: +{len(added)} / -{len(removed)} / ={len(unchanged)}")

            # UPLOAD added chunks: embed then upsert with deterministic ids
            added_infos = [ci for ci in new_infos if ci["hash"] in added]
            if added_infos:
                texts = [ci["text"] for ci in added_infos]
                embeddings = self.embedder.embed_batch(texts)

                points = []
                sparse_docs = []
                for emb, ci in zip(embeddings, added_infos):
                    payload = {"text": ci["text"], "metadata": {**ci.get("metadata", {}), "doc_id": doc_id, "pos": ci["pos"], "chunk_hash": ci["hash"]}}
                    points.append({"id": ci["point_id"], "vector": emb, "payload": payload})
                    sparse_docs.append({"id": ci["point_id"], "text": ci["text"], "metadata": payload["metadata"]})

                # upsert vector points
                self.vector_index.upsert_points(points)
                # index in sparse
                self.sparse_index.index_chunks(sparse_docs)

                # ensure chunk rows exist
                for ci in added_infos:
                    self.metadata.add_chunk_if_missing(ci["hash"], ci["point_id"])

            # DELETE removed chunks
            if removed:
                removed_point_ids = [point_id_from_chunk_hash(h) for h in removed]
                self.vector_index.delete_points(removed_point_ids)
                self.sparse_index.delete_chunks_by_ids(removed_point_ids)

            # Update doc -> chunk mapping and document metadata
            # set_doc_chunks will replace positions atomically
            chunk_infos_for_db = [{"hash": ci["hash"], "pos": ci["pos"], "point_id": ci["point_id"]} for ci in new_infos]
            self.metadata.set_doc_chunks(doc_id, chunk_infos_for_db)
            self.metadata.upsert_document(doc_id, filename, file_url, file_checksum, project)

            logger.info(f"Ingested doc {doc_id} (added: {len(added)}, removed: {len(removed)})")

        except Exception as e:
            logger.exception(f"Ingestion failed for {doc_id}: {e}")
            raise KnowledgeManagementException(str(e))

    def delete_document(self, doc_id: str):
        try:
            hashes = self.metadata.get_doc_chunk_hashes(doc_id)
            if hashes:
                point_ids = [point_id_from_chunk_hash(h) for h in hashes]
                self.vector_index.delete_points(point_ids)
                self.sparse_index.delete_chunks_by_ids(point_ids)
            self.metadata.delete_document(doc_id)
            logger.info(f"Deleted document {doc_id} and {len(hashes)} chunks")
        except Exception as e:
            logger.exception(f"Delete failed for {doc_id}: {e}")
            raise