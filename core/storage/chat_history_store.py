import sqlite3
import threading
import json
from typing import List, Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ChatHistoryStore:
    """
    SQLite-based chat history storage.
    Thread-safe for concurrent operations.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_table()

    def _init_table(self):
        """Initialize chat_history table."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Create index on timestamp for faster ordering
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_timestamp 
            ON chat_history(timestamp DESC)
            """)

            conn.commit()
            logger.debug(f"Chat history table initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize chat history table: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def save_interaction(
        self, 
        question: str, 
        answer: str, 
        sources: Optional[List[Dict]] = None
    ) -> int:
        """
        Save a question-answer interaction to chat history.

        Args:
            question: The user's question
            answer: The generated answer
            sources: List of source dicts with citation info

        Returns:
            The ID of the inserted row
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                # Convert sources list to JSON
                sources_json = json.dumps(sources) if sources else None

                cursor.execute("""
                INSERT INTO chat_history (question, answer, sources)
                VALUES (?, ?, ?)
                """, (question, answer, sources_json))

                conn.commit()
                row_id = cursor.lastrowid
                logger.debug(f"Chat interaction saved: ID={row_id}")
                return row_id

            except Exception as e:
                logger.error(f"Failed to save chat interaction: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def get_history(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Retrieve chat history ordered by newest first.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of chat history dicts
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute("""
                SELECT id, question, answer, sources, timestamp
                FROM chat_history
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """, (limit, offset))

                rows = cursor.fetchall()
                history = []

                for row in rows:
                    sources = None
                    if row[3]:  # sources column
                        try:
                            sources = json.loads(row[3])
                        except json.JSONDecodeError:
                            sources = []

                    history.append({
                        "id": row[0],
                        "question": row[1],
                        "answer": row[2],
                        "sources": sources,
                        "timestamp": row[4]
                    })

                logger.debug(f"Retrieved {len(history)} chat history records")
                return history

            except Exception as e:
                logger.error(f"Failed to retrieve chat history: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def search_history(self, query: str) -> List[Dict]:
        """
        Search chat history by question or answer.

        Args:
            query: Search term (case-insensitive)

        Returns:
            List of matching chat history dicts
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                search_term = f"%{query}%"
                cursor.execute("""
                SELECT id, question, answer, sources, timestamp
                FROM chat_history
                WHERE question LIKE ? COLLATE NOCASE
                   OR answer LIKE ? COLLATE NOCASE
                ORDER BY timestamp DESC
                """, (search_term, search_term))

                rows = cursor.fetchall()
                results = []

                for row in rows:
                    sources = None
                    if row[3]:
                        try:
                            sources = json.loads(row[3])
                        except json.JSONDecodeError:
                            sources = []

                    results.append({
                        "id": row[0],
                        "question": row[1],
                        "answer": row[2],
                        "sources": sources,
                        "timestamp": row[4]
                    })

                logger.info(f"Found {len(results)} matching chat history records")
                return results

            except Exception as e:
                logger.error(f"Failed to search chat history: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def clear_history(self) -> int:
        """
        Delete all chat history.

        Returns:
            Number of records deleted
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM chat_history")
                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Cleared {deleted_count} chat history records")
                return deleted_count

            except Exception as e:
                logger.error(f"Failed to clear chat history: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def get_chat_count(self) -> int:
        """Get total number of chat interactions."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chat_history")
                count = cursor.fetchone()[0]
                return count
            finally:
                conn.close()
