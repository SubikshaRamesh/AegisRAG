import sqlite3
import threading
import json
from datetime import datetime
from typing import List, Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ChatHistoryStore:
    """
    SQLite-based chat history storage supporting multi-message conversations.
    Thread-safe for concurrent operations.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_tables()

    def _init_tables(self):
        """Initialize conversations and messages tables."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            cursor = conn.cursor()

            # Conversations table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                chat_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """)

            # Messages table (supports multiple messages per chat)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES conversations (chat_id)
            )
            """)

            # Create indexes for faster queries
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id 
            ON messages(chat_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
            ON conversations(created_at DESC)
            """)

            # Legacy chat_history table (kept for backward compatibility)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_timestamp 
            ON chat_history(timestamp DESC)
            """)

            conn.commit()
            logger.debug(f"Chat history tables initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize chat history tables: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def create_conversation(self, chat_id: str, title: str) -> bool:
        """
        Create a new conversation.

        Args:
            chat_id: Unique chat identifier (UUID)
            title: First user message (truncated)

        Returns:
            True if successful, False if already exists
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()

                cursor.execute("""
                INSERT INTO conversations (chat_id, title, created_at)
                VALUES (?, ?, ?)
                """, (chat_id, title, now))

                conn.commit()
                logger.debug(f"Conversation created: chat_id={chat_id}")
                return True

            except sqlite3.IntegrityError:
                logger.warning(f"Conversation already exists: chat_id={chat_id}")
                return False
            except Exception as e:
                logger.error(f"Failed to create conversation: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def conversation_exists(self, chat_id: str) -> bool:
        """Check if a conversation exists."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM conversations WHERE chat_id = ?", (chat_id,))
                return cursor.fetchone() is not None
            except Exception as e:
                logger.error(f"Failed to check conversation: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None
    ) -> bool:
        """
        Add a message to a conversation.

        Args:
            chat_id: Chat identifier
            role: Message role (user or assistant)
            content: Message content
            sources: Optional list of source dicts

        Returns:
            True if successful
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                sources_json = json.dumps(sources) if sources else None

                cursor.execute("""
                INSERT INTO messages (chat_id, role, content, sources, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (chat_id, role, content, sources_json, now))

                conn.commit()
                logger.debug(f"Message added to chat_id={chat_id}, role={role}")
                return True

            except Exception as e:
                logger.error(f"Failed to add message: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def get_conversation(self, chat_id: str) -> Optional[Dict]:
        """
        Get all messages in a conversation ordered by timestamp.

        Args:
            chat_id: Chat identifier

        Returns:
            Dict with chat_id and ordered messages, or None if not found
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                # Verify conversation exists
                cursor.execute("SELECT title, created_at FROM conversations WHERE chat_id = ?", (chat_id,))
                conv_row = cursor.fetchone()
                if not conv_row:
                    return None

                # Get all messages
                cursor.execute("""
                SELECT role, content, sources, timestamp
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp ASC
                """, (chat_id,))

                messages = []
                for row in cursor.fetchall():
                    sources = None
                    if row[2]:  # sources column
                        try:
                            sources = json.loads(row[2])
                        except json.JSONDecodeError:
                            sources = []

                    messages.append({
                        "role": row[0],
                        "content": row[1],
                        "sources": sources,
                        "timestamp": row[3]
                    })

                logger.debug(f"Retrieved {len(messages)} messages for chat_id={chat_id}")
                return {
                    "chat_id": chat_id,
                    "title": conv_row[0],
                    "created_at": conv_row[1],
                    "messages": messages
                }

            except Exception as e:
                logger.error(f"Failed to get conversation: {e}", exc_info=True)
                raise
            finally:
                conn.close()

    def list_conversations(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Get list of all conversations ordered by newest first.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of conversation summaries
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            try:
                cursor = conn.cursor()

                cursor.execute("""
                SELECT chat_id, title, created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """, (limit, offset))

                conversations = []
                for row in cursor.fetchall():
                    conversations.append({
                        "chat_id": row[0],
                        "title": row[1],
                        "created_at": row[2]
                    })

                logger.debug(f"Retrieved {len(conversations)} conversations")
                return conversations

            except Exception as e:
                logger.error(f"Failed to list conversations: {e}", exc_info=True)
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
