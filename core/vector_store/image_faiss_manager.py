import faiss
import numpy as np
import os
import pickle
import threading
from typing import List, Set
from core.schema.chunk import Chunk
from core.logger import get_logger

logger = get_logger(__name__)


class ImageFaissManager:
    def __init__(
        self,
        embedding_dim: int = 512,
        index_path: str = "data/image_faiss.index",
        meta_path: str = "data/image_chunk_ids.pkl"
    ):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.meta_path = meta_path

        # Thread safety for concurrent operations
        self._lock = threading.RLock()

        os.makedirs(os.path.dirname(index_path), exist_ok=True)

        if os.path.exists(index_path) and os.path.exists(meta_path):
            self._load()
        else:
            self.index = faiss.IndexFlatL2(embedding_dim)
            self.chunk_ids: List[str] = []

        # Cache chunk_ids as set for O(1) duplicate detection
        self._chunk_ids_set: Set[str] = set(self.chunk_ids)

    # ----------------------------
    # Add embeddings (with deduplication)
    # ----------------------------
    def add(self, embeddings: np.ndarray, chunks: List[Chunk]) -> int:
        """
        Add embeddings with duplicate detection.
        
        Returns:
            Number of chunks actually added
        """
        with self._lock:
            # Filter out duplicates
            new_chunks = []
            new_embeddings = []

            for i, chunk in enumerate(chunks):
                if chunk.chunk_id in self._chunk_ids_set:
                    logger.warning(
                        f"Duplicate image chunk_id detected: {chunk.chunk_id}. Skipping."
                    )
                    continue

                new_chunks.append(chunk)
                new_embeddings.append(embeddings[i])

            if not new_chunks:
                logger.info("No new image chunks to add (all duplicates)")
                return 0

            # Add only new vectors
            new_embeddings = np.array(new_embeddings, dtype=np.float32)
            faiss.normalize_L2(new_embeddings)
            self.index.add(new_embeddings)

            # Update tracking
            for chunk in new_chunks:
                self.chunk_ids.append(chunk.chunk_id)
                self._chunk_ids_set.add(chunk.chunk_id)

            logger.info(f"Added {len(new_chunks)} new image vectors to FAISS index")
            return len(new_chunks)

    # ----------------------------
    # Search
    # ----------------------------
    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        DISTANCE_THRESHOLD = 1.0
        query_embedding = query_embedding.astype(np.float32)
        faiss.normalize_L2(query_embedding)

        with self._lock:
            distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if 0 <= idx < len(self.chunk_ids) and dist <= DISTANCE_THRESHOLD:
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "distance": float(dist)
                })

        return results

    # ----------------------------
    # Save to disk (thread-safe)
    # ----------------------------
    def save(self):
        with self._lock:
            faiss.write_index(self.index, self.index_path)
            with open(self.meta_path, "wb") as f:
                pickle.dump(self.chunk_ids, f)
            logger.debug(f"Saved image FAISS index: {len(self.chunk_ids)} chunks")

    # ----------------------------
    # Load from disk
    # ----------------------------
    def _load(self):
        with self._lock:
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, "rb") as f:
                self.chunk_ids = pickle.load(f)
            logger.info(f"Loaded image FAISS index: {len(self.chunk_ids)} chunks")

    # ----------------------------
    # Reset (optional)
    # ----------------------------
    def reset(self):
        with self._lock:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.chunk_ids = []
            self._chunk_ids_set.clear()

            if os.path.exists(self.index_path):
                os.remove(self.index_path)
            if os.path.exists(self.meta_path):
                os.remove(self.meta_path)
            logger.info("Image FAISS index reset")
