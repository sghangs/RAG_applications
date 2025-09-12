import hashlib
import requests
from ingestion.parsers.parse_factory import ParserFactory
from ingestion.chunking.smart_chunker import SmartChunker
from ingestion.embedding.embedder import Embedder
from ingestion.indexing.vector_index import VectorIndex
from ingestion.indexing.sparse_index import SparseIndex
from ingestion.indexing.metadata_store import MetadataStore
from ingestion.utils.logger import get_logger
from ingestion.utils.exceptions import KnowledgeManagementException

logger = get_logger(__name__)

def _checksum(content: bytes) -> str:
    """Generate checksum for deduplication/update detection."""
    return hashlib.sha256(content).hexdigest()


def run_ingestion(file_url: str, doc_id: str, project: str, event_type: str = "created"):
    """
    Ingest or update or delete document into vector/sparse indexes.
    
    Args:
        file_url (str): Download URL of the file
        doc_id (str): Unique identifier (SharePoint item ID)
        project (str): Project name
        event_type (str): "created", "updated", or "deleted"
    """
    try:
        metadata_store = MetadataStore("postgres://user:pwd@localhost/db")
        vector_index = VectorIndex()
        sparse_index = SparseIndex()
        embedder = Embedder()
        chunker = SmartChunker()

        # Handle delete
        if event_type == "deleted":
            logger.info(f"Deleting document {doc_id} from indexes")
            vector_index.delete(doc_id)
            sparse_index.delete(doc_id)
            metadata_store.delete_document(doc_id)
            return

        # Download content
        resp = requests.get(file_url)
        if resp.status_code != 200:
            raise KnowledgeManagementException(f"Failed to download file: {resp.text}")
        content = resp.content

        checksum = _checksum(content)
        old_checksum = metadata_store.get_checksum(doc_id)

        # Skip if no change
        if event_type == "updated" and checksum == old_checksum:
            logger.info(f"Document {doc_id} unchanged, skipping re-ingestion")
            return

        # Parse
        parser = ParserFactory.get_parser(file_url)
        blocks = parser.parse(content)

        # Chunk
        chunks = chunker.chunk(blocks)

        # Embed
        embeddings = embedder.embed_batch([c["text"] for c in chunks])

        # Upsert
        vector_index.upsert(embeddings, chunks, doc_id=doc_id)
        sparse_index.index_chunks(chunks, doc_id=doc_id)

        # Update metadata
        metadata_store.upsert_document(
            doc_id, title=file_url.split("/")[-1],
            uri=file_url, checksum=checksum, project=project
        )

        logger.info(f"Ingestion complete for {doc_id}, event={event_type}")

    except Exception as e:
        raise KnowledgeManagementException(f"Pipeline ingestion failed: {str(e)}")
