import os
from connectors.local import LocalConnector
from parsers.parser_factory import ParserFactory
from chunking.smart_chunker import SmartChunker
from embedding.embedder import Embedder
from indexing.vector_index import VectorIndex
from indexing.sparse_index import SparseIndex
from indexing.metadata_store import MetadataStore
from utils.logger import logger
from exceptions import KnowledgeManagementException


class IngestionPipeline:
    """
    Orchestrates file ingestion:
    - Fetch file (from raw folder or other connector)
    - Parse & preprocess
    - Chunk
    - Embed
    - Index (vector + sparse)
    - Store metadata
    """

    def __init__(self, raw_folder="data/raw"):
        self.raw_folder = raw_folder
        self.connector = LocalConnector()
        self.chunker = SmartChunker()
        self.embedder = Embedder()
        self.vector_index = VectorIndex()
        self.sparse_index = SparseIndex()
        self.metadata_store = MetadataStore("postgres://user:pwd@localhost/db")

    def run(self):
        try:
            files = [f for f in os.listdir(self.raw_folder) if os.path.isfile(os.path.join(self.raw_folder, f))]
            logger.info(f"Discovered {len(files)} files in {self.raw_folder}")

            for filename in files:
                filepath = os.path.join(self.raw_folder, filename)
                logger.info(f"Processing {filepath}")

                try:
                    content = self.connector.fetch(filepath)
                    blocks = ParserFactory.parse_and_clean(filename, content)

                    chunks = self.chunker.chunk(blocks)
                    logger.info(f"Generated {len(chunks)} chunks for {filename}")

                    embeddings = self.embedder.embed_batch([c["text"] for c in chunks])

                    self.vector_index.upsert(embeddings, chunks)
                    self.sparse_index.index_chunks(chunks)

                    self.metadata_store.upsert_document(
                        doc_id=filename,  # replace with UUID if needed
                        title=filename,
                        uri=filepath,
                        checksum="checksum123",  # TODO: replace with real hash
                        project="KnowledgeBase"
                    )

                    logger.info(f"Successfully ingested {filename}")

                except KnowledgeManagementException as e:
                    logger.error(f"Pipeline error for {filename}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error for {filename}: {e}")

        except Exception as e:
            raise KnowledgeManagementException(
                f"Pipeline failed: {e}",
                None,
                "IngestionPipeline"
            )


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run()
