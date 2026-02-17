import sqlite3
import threading
from typing import List, Optional
from core.schema.chunk import Chunk
from core.logger import get_logger

logger = get_logger(__name__)


class MetadataStore:
    """
    SQLite-based metadata storage with transaction management.
    Thread-safe for concurrent operations.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            cursor = conn.cursor()

            # Create chunks table with proper indices
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

            # Create indices for common queries
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_file 
            ON chunks(source_file)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_type 
            ON chunks(source_type)
            """)

            conn.commit()
            logger.debug(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def save_chunks(self, chunks: List[Chunk]) -> int:
        """
        Save chunks to database with transaction management.
        
        Args:
            chunks: List of Chunk objects to save
            
        Returns:
            Number of chunks actually inserted (excluding conflicts)
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                # Start transaction
                cursor.execute("BEGIN TRANSACTION")

                inserted_count = 0
                for chunk in chunks:
                    cursor.execute("""
                    INSERT OR IGNORE INTO chunks
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
                    # Only count if row was actually inserted
                    if cursor.rowcount > 0:
                        inserted_count += 1

                # Commit transaction
                conn.commit()
                logger.debug(f"Saved {inserted_count} chunks to database")
                return inserted_count

            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to save chunks: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """
        Retrieve a single chunk by ID.
        
        Args:
            chunk_id: The chunk ID to retrieve
            
        Returns:
            Chunk object or None if not found
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT chunk_id, text, source_type, source_file, page_number, timestamp "
                    "FROM chunks WHERE chunk_id = ?",
                    (chunk_id,)
                )

                row = cursor.fetchone()

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
            finally:
                conn.close()

    def get_chunks_by_source(self, source_file: str) -> List[Chunk]:
        """
        Retrieve all chunks from a specific source file.
        Useful for duplicate detection before reingest.
        
        Args:
            source_file: The source file name
            
        Returns:
            List of Chunk objects from that source
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT chunk_id, text, source_type, source_file, page_number, timestamp "
                    "FROM chunks WHERE source_file = ?",
                    (source_file,)
                )

                rows = cursor.fetchall()
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
            finally:
                conn.close()

    def get_all_chunks(self) -> List[Chunk]:
        """
        Retrieve all chunks from database.
        
        Returns:
            List of all Chunk objects
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT chunk_id, text, source_type, source_file, page_number, timestamp "
                    "FROM chunks"
                )

                rows = cursor.fetchall()
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
                logger.debug(f"Retrieved {len(chunks)} chunks from database")
                return chunks
            finally:
                conn.close()

    def get_chunk_count(self) -> int:
        """Get total number of chunks in database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chunks")
                count = cursor.fetchone()[0]
                return count
            finally:
                conn.close()

    def delete_chunks_by_source(self, source_file: str) -> int:
        """
        Delete all chunks from a specific source file.
        Useful for cleanup or re-ingestion.
        
        Args:
            source_file: The source file name
            
        Returns:
            Number of chunks deleted
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute("BEGIN TRANSACTION")
                cursor.execute("DELETE FROM chunks WHERE source_file = ?", (source_file,))
                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Deleted {deleted_count} chunks from source: {source_file}")
                return deleted_count
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to delete chunks: {e}", exc_info=True)
                raise
            finally:
                conn.close()
