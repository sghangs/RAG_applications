from utils.logger import logger
from exceptions import KnowledgeManagementException
from parsers.parser_factory import ParserFactory
from preprocessing.cleaner import TextCleaner
from chunking.smart_chunker import SmartChunker
import os


class IngestionPipeline:
    def __init__(self, input_dir="data/raw"):
        self.input_dir = input_dir
        self.cleaner = TextCleaner()
        self.chunker = SmartChunker(max_tokens=500, overlap=50)

    def run(self):
        logger.info(f"Starting ingestion pipeline on {self.input_dir}")

        if not os.path.exists(self.input_dir):
            raise KnowledgeManagementException("Input directory not found", self.input_dir, "PipelineInit")

        results = {}

        for filename in os.listdir(self.input_dir):
            file_path = os.path.join(self.input_dir, filename)
            if not os.path.isfile(file_path):
                continue

            logger.info(f"Processing file: {filename}")

            try:
                with open(file_path, "rb") as f:
                    content = f.read()

                parser = ParserFactory.get_parser(filename, content)
                blocks = parser.parse(content)

                # 🔹 NEW: clean parsed blocks
                cleaned_blocks = self.cleaner.clean_blocks(blocks)

                # 🔹 Chunking
                chunks = self.chunker.chunk(cleaned_blocks)

                results[filename] = chunks
                logger.info(f"Processed {filename}: {len(blocks)} raw → {len(cleaned_blocks)} cleaned → {len(chunks)} chunks")

            except KnowledgeManagementException as e:
                logger.error(f"KnowledgeManagementException: {e}")
            except Exception as e:
                logger.error(f"Unhandled error in {filename}: {str(e)}")
                raise KnowledgeManagementException(str(e), filename, "Parsing")

        return results
