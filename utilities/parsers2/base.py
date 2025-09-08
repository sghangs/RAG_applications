from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> list[dict]:
        """Return list of blocks with text + metadata."""
        pass