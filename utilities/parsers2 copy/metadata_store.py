import psycopg2

class MetadataStore:
    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)

    def upsert_document(self, doc_id, title, uri, checksum, project):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO documents (id, title, source_uri, checksum, project)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET title = EXCLUDED.title,
                          source_uri = EXCLUDED.source_uri,
                          checksum = EXCLUDED.checksum,
                          project = EXCLUDED.project,
                          updated_at = now()
        """, (doc_id, title, uri, checksum, project))
        self.conn.commit()

    def get_checksum(self, doc_id):
        cur = self.conn.cursor()
        cur.execute("SELECT checksum FROM documents WHERE id=%s", (doc_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def delete_document(self, doc_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM documents WHERE id=%s", (doc_id,))
        self.conn.commit()
