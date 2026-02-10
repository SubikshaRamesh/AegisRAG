import sqlite3
from typing import List
from core.schema.chunk import Chunk


class MetadataStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_file TEXT NOT NULL,
            page_number INTEGER,
            timestamp REAL
        )
        """)

        conn.commit()
        conn.close()

    def save_chunks(self, chunks: List[Chunk]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for chunk in chunks:
            cursor.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, text, source_type, source_file, page_number, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id,
                chunk.text,
                chunk.source_type,
                chunk.source_file,
                chunk.page_number,
                chunk.timestamp
            ))

        conn.commit()
        conn.close()

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT chunk_id, text, source_type, source_file, page_number, timestamp FROM chunks WHERE chunk_id = ?",
            (chunk_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Chunk(
            chunk_id=row[0],
            text=row[1],
            source_type=row[2],
            source_file=row[3],
            page_number=row[4],
            timestamp=row[5]
        )
    def get_all_chunks(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT chunk_id, text, source_type, source_file, page_number, timestamp FROM chunks"
        )

        rows = cursor.fetchall()
        conn.close()

        chunks = []
        for row in rows:
            chunks.append(Chunk(
                chunk_id=row[0],
                text=row[1],
                source_type=row[2],
                source_file=row[3],
                page_number=row[4],
                timestamp=row[5]
            ))

        return chunks
