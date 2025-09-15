"""
Metadata store using Postgres (psycopg2) storing: documents, chunks, doc_chunks
- documents: id (text), title, uri, checksum, project, updated_at
- chunks: chunk_hash (pk), point_id, created_at
- doc_chunks: doc_id, chunk_hash, position

This implementation uses psycopg2 and JSONB where helpful. For production you may prefer SQLAlchemy.
"""
import psycopg2
import psycopg2.extras
import json
from typing import List, Dict, Set, Optional
from datetime import datetime


class MetadataStore:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = psycopg2.connect(dsn)
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT,
                uri TEXT,
                checksum TEXT,
                project TEXT,
                updated_at TIMESTAMP DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_hash TEXT PRIMARY KEY,
                point_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS doc_chunks (
                doc_id TEXT,
                chunk_hash TEXT,
                position INTEGER,
                PRIMARY KEY (doc_id, chunk_hash),
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (chunk_hash) REFERENCES chunks(chunk_hash) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()
        cur.close()

    # Documents
    def upsert_document(self, doc_id: str, title: str, uri: str, checksum: str, project: str):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (id, title, uri, checksum, project, updated_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, uri = EXCLUDED.uri,
              checksum = EXCLUDED.checksum, project = EXCLUDED.project, updated_at = now();
            """,
            (doc_id, title, uri, checksum, project),
        )
        self.conn.commit()
        cur.close()

    def get_checksum(self, doc_id: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT checksum FROM documents WHERE id=%s", (doc_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    def delete_document(self, doc_id: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM documents WHERE id=%s", (doc_id,))
        self.conn.commit()
        cur.close()

    # Chunk operations
    def chunk_exists(self, chunk_hash: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM chunks WHERE chunk_hash=%s", (chunk_hash,))
        exists = cur.fetchone() is not None
        cur.close()
        return exists

    def add_chunk_if_missing(self, chunk_hash: str, point_id: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO chunks (chunk_hash, point_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (chunk_hash, point_id),
        )
        self.conn.commit()
        cur.close()

    def set_doc_chunks(self, doc_id: str, chunk_infos: List[Dict]):
        """
        Replace doc_chunks for doc_id with new positions. chunk_infos: list of {hash, point_id, pos}
        This is atomic in a transaction.
        """
        cur = self.conn.cursor()
        try:
            # ensure document exists
            cur.execute("SELECT 1 FROM documents WHERE id=%s", (doc_id,))
            if cur.fetchone() is None:
                # create a placeholder doc row (checksum can be set later by caller)
                cur.execute("INSERT INTO documents (id, title, uri, checksum, project, updated_at) VALUES (%s,%s,%s,%s,%s,now())",
                            (doc_id, doc_id, doc_id, None, None))

            # delete existing mappings
            cur.execute("DELETE FROM doc_chunks WHERE doc_id=%s", (doc_id,))

            # insert new mappings
            insert_vals = [(doc_id, ci["hash"], ci["pos"]) for ci in chunk_infos]
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO doc_chunks (doc_id, chunk_hash, position) VALUES %s",
                insert_vals,
            )
            self.conn.commit()
        finally:
            cur.close()

    def get_doc_chunk_hashes(self, doc_id: str) -> Set[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT chunk_hash FROM doc_chunks WHERE doc_id=%s ORDER BY position", (doc_id,))
        rows = cur.fetchall()
        cur.close()
        return {r[0] for r in rows} if rows else set()

    def get_doc_chunk_infos(self, doc_id: str) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT chunk_hash, position FROM doc_chunks WHERE doc_id=%s ORDER BY position", (doc_id,))
        rows = cur.fetchall()
        cur.close()
        return [{"hash": r[0], "position": r[1]} for r in rows]

    def get_point_id_for_hash(self, chunk_hash: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT point_id FROM chunks WHERE chunk_hash=%s", (chunk_hash,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    def close(self):
        self.conn.close()