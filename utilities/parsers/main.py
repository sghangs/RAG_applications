from parsers.parser_factory import ParserFactory

def ingest_file(filename: str, content: bytes):
    parser = ParserFactory.get_parser(filename, content)
    blocks = parser.parse(content)
    return blocks

# Example
with open("weirdly_named_file.noext", "rb") as f:
    content = f.read()

blocks = ingest_file("weirdly_named_file.noext", content)
print(blocks[:2])
