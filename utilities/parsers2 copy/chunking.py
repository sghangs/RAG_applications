from typing import List, Dict
import re


_sentence_splitter_re = re.compile(r'(?<=[.!?])\s+')




class StableChunker:
    def __init__(self, words_per_chunk: int = 150, overlap_words: int = 30):
        assert words_per_chunk > overlap_words, "words_per_chunk must be greater than overlap"
        self.words_per_chunk = words_per_chunk
        self.overlap_words = overlap_words


    def _split_sentences(self, text: str) -> List[str]:
        # naive sentence split; works well enough for many docs
        sentences = [s.strip() for s in _sentence_splitter_re.split(text) if s.strip()]
        return sentences


    def _sentences_to_words(self, sentences: List[str]) -> List[str]:
        # produce a word list preserving order
        words = []
        for s in sentences:
            # split on whitespace
            ws = [w for w in s.split() if w]
            words.extend(ws)
        return words


    def chunk(self, blocks: List[Dict]) -> List[Dict]:
        """
        Accepts list of blocks: {text, metadata}
        Returns list of chunks: {text, metadata}
        """
        chunks = []
        for block in blocks:
            text = block.get("text", "")
            meta = block.get("metadata", {})
            if not text or not text.strip():
                continue


            sentences = self._split_sentences(text)
            words = self._sentences_to_words(sentences)


            i = 0
            n = len(words)
            step = self.words_per_chunk - self.overlap_words
            if step <= 0:
                step = self.words_per_chunk


            while i < n:
                chunk_words = words[i: i + self.words_per_chunk]
                if not chunk_words:
                    break
                chunk_text = " ".join(chunk_words).strip()
                chunks.append({"text": chunk_text, "metadata": meta})
                i += step

        return chunks