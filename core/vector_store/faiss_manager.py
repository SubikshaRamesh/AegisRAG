import faiss
import numpy as np
from typing import List
from core.schema.chunk import Chunk


class FaissManager:
    def __init__(self, embedding_dim: int):
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.chunk_ids: List[str] = []

    def add(self, embeddings: np.ndarray, chunks: List[Chunk]):
        """
        Add embeddings and corresponding chunks to FAISS.
        """
        self.index.add(embeddings)
        self.chunk_ids.extend([chunk.chunk_id for chunk in chunks])

    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        """
        Search FAISS index and return top-k chunk IDs.
        """
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.chunk_ids):
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "distance": float(dist)
                })

        return results
