import re
import string
from nltk.corpus import stopwords
from utils.logger import logger
from exceptions import KnowledgeManagementException


class TextCleaner:
    """
    Applies configurable preprocessing to text blocks
    """

    def __init__(self, config: dict):
        self.config = config
        self.stopwords = set(stopwords.words("english"))

    def clean(self, blocks: list[dict]) -> list[dict]:
        cleaned_blocks = []
        try:
            for block in blocks:
                text = block["text"]

                if self.config.get("lowercase", False):
                    text = text.lower()

                if self.config.get("remove_punctuation", False):
                    text = text.translate(str.maketrans("", "", string.punctuation))

                if self.config.get("normalize_whitespace", False):
                    text = re.sub(r"\s+", " ", text).strip()

                if self.config.get("remove_stopwords", False):
                    words = [w for w in text.split() if w not in self.stopwords]
                    text = " ".join(words)

                cleaned_blocks.append({
                    "text": text,
                    "metadata": block["metadata"]
                })

            return cleaned_blocks

        except Exception as e:
            raise KnowledgeManagementException(
                f"Text cleaning failed: {e}",
                None,
                "TextCleaner"
            )
