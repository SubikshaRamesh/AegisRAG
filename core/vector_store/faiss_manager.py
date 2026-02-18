import faiss
import numpy as np
import os
import pickle
import threading
from typing import List, Set
from core.schema.chunk import Chunk
from core.logger import get_logger

logger = get_logger(__name__)


class FaissManager:
    def __init__(
        self,
        embedding_dim: int,
        index_path: str = "data/faiss.index",
        meta_path: str = "data/chunk_ids.pkl"
    ):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.meta_path = meta_path

        # Thread safety for concurrent operations
        self._lock = threading.RLock()

        # Ensure data folder exists
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
        
        Args:
            embeddings: numpy array of embeddings
            chunks: list of Chunk objects
            
        Returns:
            Number of chunks actually added (excluding duplicates)
        """
        with self._lock:
            # Filter out duplicates
            new_chunks = []
            new_embeddings = []

            for i, chunk in enumerate(chunks):
                if chunk.chunk_id in self._chunk_ids_set:
                    logger.warning(
                        f"Duplicate chunk_id detected: {chunk.chunk_id}. Skipping."
                    )
                    continue

                new_chunks.append(chunk)
                new_embeddings.append(embeddings[i])

            if not new_chunks:
                logger.info("No new chunks to add (all duplicates)")
                return 0

            # Add only new vectors
            new_embeddings = np.array(new_embeddings, dtype=np.float32)
            faiss.normalize_L2(new_embeddings)
            self.index.add(new_embeddings)

            # Update tracking
            for chunk in new_chunks:
                self.chunk_ids.append(chunk.chunk_id)
                self._chunk_ids_set.add(chunk.chunk_id)

            logger.info(f"Added {len(new_chunks)} new vectors to FAISS index")
            return len(new_chunks)

    # ----------------------------
    # Search
    # ----------------------------
    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        """
        Search FAISS index with query embedding.
        
        IMPORTANT:
        After switching embedding models (e.g., all-MiniLM-L6-v2 to multilingual),
        L2 distances change significantly. Strict distance thresholds can filter out
        valid results. This implementation returns top_k results without aggressive
        filtering to ensure retrieval works across different embedding models.
        
        Only invalid indices (-1) are filtered out.
        """
        query_embedding = query_embedding.astype(np.float32)
        
        # DEBUG: Log query and index dimensions
        logger.info("[DEBUG RETRIEVAL] --- FAISS SEARCH DEBUG START ---")
        logger.info(f"[DEBUG RETRIEVAL] Query embedding shape: {query_embedding.shape}")
        query_dim = query_embedding.shape[1] if len(query_embedding.shape) > 1 else query_embedding.shape[0]
        logger.info(f"[DEBUG RETRIEVAL] Query embedding dimension: {query_dim}D")
        logger.info(f"[DEBUG RETRIEVAL] FAISS index.d (embedding dim): {self.index.d}D")
        logger.info(f"[DEBUG RETRIEVAL] FAISS index.ntotal (vectors stored): {self.index.ntotal}")
        logger.info(f"[DEBUG RETRIEVAL] Chunk IDs count: {len(self.chunk_ids)}")
        
        # Check dimension mismatch
        if query_dim != self.index.d:
            logger.error(f"[DEBUG RETRIEVAL] DIMENSION MISMATCH! Query: {query_dim}, Index: {self.index.d}")
            # This is a critical error - cannot proceed
            raise ValueError(f"Embedding dimension mismatch: query={query_dim}, index={self.index.d}")
        else:
            logger.info(f"[DEBUG RETRIEVAL] Embeddings match: {query_dim}D")
        
        # Normalize for L2 distance
        faiss.normalize_L2(query_embedding)

        with self._lock:
            distances, indices = self.index.search(query_embedding, top_k)

        # DEBUG: Log raw FAISS results
        logger.info(f"[DEBUG RETRIEVAL] Raw FAISS search returned {len(indices[0])} results")
        logger.info(f"[DEBUG RETRIEVAL] Raw distances (L2): {distances[0]}")
        logger.info(f"[DEBUG RETRIEVAL] Raw indices: {indices[0]}")
        
        results = []
        invalid_count = 0
        
        # Return all valid results (no aggressive distance filtering)
        for idx, dist in zip(indices[0], distances[0]):
            # Only filter out invalid indices (-1)
            if 0 <= idx < len(self.chunk_ids):
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "distance": float(dist)
                })
                logger.info(f"[DEBUG RETRIEVAL] ✓ INCLUDED: idx={idx}, distance={dist:.4f}, chunk_id={self.chunk_ids[idx][:20]}...")
            else:
                invalid_count += 1
                logger.warning(f"[DEBUG RETRIEVAL] Invalid index: {idx} (FAISS returns -1 for missing results)")

        logger.info(f"[DEBUG RETRIEVAL] Final results: {len(results)}/{top_k} valid (invalid: {invalid_count})")
        logger.info("[DEBUG RETRIEVAL] --- FAISS SEARCH DEBUG END ---")
        
        return results

    # ----------------------------
    # Save index to disk (thread-safe)
    # ----------------------------
    def save(self):
        with self._lock:
            faiss.write_index(self.index, self.index_path)
            with open(self.meta_path, "wb") as f:
                pickle.dump(self.chunk_ids, f)
            logger.debug(f"Saved FAISS index: {len(self.chunk_ids)} chunks")

    # ----------------------------
    # Load index from disk
    # ----------------------------
    def _load(self):
        with self._lock:
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, "rb") as f:
                self.chunk_ids = pickle.load(f)
            logger.info(f"Loaded FAISS index: {len(self.chunk_ids)} chunks")

    # ----------------------------
    # Clear index (optional utility)
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
            logger.info("FAISS index reset")
