import hashlib
import uuid

def compute_checksum(content: bytes, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    h.update(content)
    return h.hexdigest()


def chunk_text_hash(text: str) -> str:
    """Canonicalize and return sha256 hex digest of a chunk's text."""
    # canonicalize: normalize whitespace and Unicode, strip surrounding whitespace
    normalized = " ".join(text.split())
    h = hashlib.sha256(normalized.encode("utf-8"))
    return h.hexdigest()


def point_id_from_chunk_hash(chunk_hash: str) -> str:
    """Deterministic uuid v5 based on chunk_hash (stable across runs)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_hash))