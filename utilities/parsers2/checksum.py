import hashlib

def calculate_checksum(content: bytes, algo="sha256") -> str:
    h = hashlib.new(algo)
    h.update(content)
    return h.hexdigest()

def calculate_text_checksum(text: str, algo="sha256") -> str:
    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return h.hexdigest()
