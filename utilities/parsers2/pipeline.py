# pipeline.py
import io
from parsers.parser_factory import ParserFactory
from preprocessing.cleaner import TextCleaner
from chunking.smart_chunker import SmartChunker
from embedding.embedder import Embedder
from indexing.vector_index import VectorIndex
from indexing.sparse_index import SparseIndex
from indexing.metadata_store import MetadataStore
from utils.logger import logger
from utils.checksum import calculate_checksum, calculate_text_checksum
from exceptions import KnowledgeManagementException

class IngestionPipeline:
    def __init__(self):
        self.cleaner = TextCleaner()  # default config usage; or pass config
        self.chunker = SmartChunker()
        self.embedder = Embedder()
        self.vector_index = VectorIndex()
        self.sparse_index = SparseIndex()
        self.metadata_store = MetadataStore()

    def ingest(self, filename: str, content: bytes, project: str = "KnowledgeBase"):
        """
        Ingest or update a document. Performs chunk-diffing and only re-embeds changed chunks.
        """
        try:
            file_checksum = calculate_checksum(content)
            doc_id = filename  # use a stable doc id strategy in prod (UUID, SharePoint id, etc.)

            existing_doc = self.metadata_store.get_document(doc_id)
            if existing_doc and existing_doc.get("checksum") == file_checksum:
                logger.info(f"[Pipeline] No changes for {doc_id} (checksum match) — skipping.")
                return

            # Parse + clean
            blocks = ParserFactory.parse_and_clean(filename, content)

            # Chunk
            chunks = self.chunker.chunk(blocks)

            # assign deterministic chunk ids and compute per-chunk checksum
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}__chunk_{i}"
                chunk["id"] = chunk_id
                chunk["checksum"] = calculate_text_checksum(chunk["text"])

            # Determine which chunks changed
            old_chunks_map = self.metadata_store.get_chunks(doc_id) or {}
            changed_chunks = []
            removed_chunk_ids = []
            new_embeddings_texts = []
            new_chunk_ids = []

            # find changed or new chunks
            for c in chunks:
                old_checksum = old_chunks_map.get(c["id"])
                if old_checksum != c["checksum"]:
                    changed_chunks.append(c)
                    new_embeddings_texts.append(c["text"])
                    new_chunk_ids.append(c["id"])

            # find deleted chunks (present previously but not in new set)
            new_chunk_id_set = {c["id"] for c in chunks}
            for old_id in old_chunks_map.keys():
                if old_id not in new_chunk_id_set:
                    removed_chunk_ids.append(old_id)

            # Process deletes first (so we don't have duplicates)
            if removed_chunk_ids:
                logger.info(f"[Pipeline] Deleting {len(removed_chunk_ids)} removed chunks for {doc_id}")
                self.vector_index.delete_points(removed_chunk_ids)
                self.sparse_index.delete_chunks(removed_chunk_ids)
                self.metadata_store.remove_chunks(doc_id, removed_chunk_ids)

            # Embed & upsert changed chunks
            if changed_chunks:
                embeddings = self.embedder.embed_batch(new_embeddings_texts)
                # NOTE: embed_batch must preserve order aligned with new_embeddings_texts
                # upsert into vector index using chunk objects (use embedding alignment)
                self.vector_index.upsert(embeddings, changed_chunks)
                self.sparse_index.index_chunks(changed_chunks)

            # Update metadata (store new doc checksum & chunk map)
            self.metadata_store.upsert_document(
                doc_id=doc_id,
                title=filename,
                uri=filename,
                checksum=file_checksum,
                project=project,
                chunks=chunks
            )

            logger.info(f"[Pipeline] Ingested {doc_id}: {len(changed_chunks)} changed, {len(removed_chunk_ids)} removed.")

        except Exception as e:
            logger.exception(f"[Pipeline] ingest failed for {filename}: {e}")
            raise KnowledgeManagementException(str(e), filename, "IngestionPipeline")

    def delete_document(self, doc_id: str):
        """
        Fully delete a document and its chunks from all indexes and metadata store.
        """
        try:
            existing = self.metadata_store.get_document(doc_id)
            if not existing:
                logger.warning(f"[Pipeline] delete request for unknown doc {doc_id}")
                return

            chunk_ids = list(existing.get("chunks", {}).keys())
            if chunk_ids:
                self.vector_index.delete_points(chunk_ids)
                self.sparse_index.delete_chunks(chunk_ids)

            self.metadata_store.delete_document(doc_id)
            logger.info(f"[Pipeline] Deleted document {doc_id} and {len(chunk_ids)} chunks.")
        except Exception as e:
            logger.exception(f"[Pipeline] delete failed for {doc_id}: {e}")
            raise KnowledgeManagementException(str(e), doc_id, "IngestionPipeline.delete")
