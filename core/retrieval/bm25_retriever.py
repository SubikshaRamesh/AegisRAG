from rank_bm25 import BM25Okapi
from typing import List, Dict
import numpy as np

from core.storage.metadata_store import MetadataStore
from core.schema.chunk import Chunk


class BM25Retriever:
    """
    Sparse retrieval using BM25.
    Loads all chunk texts from SQLite and builds a BM25 index.
    """

    def __init__(self, metadata_store: MetadataStore):

       self.store = metadata_store

       chunks: List[Chunk] = self.store.get_all_chunks()

       self.chunks = chunks
       self.chunk_map = {c.chunk_id: c for c in chunks}

       corpus = [c.text.split() for c in chunks]

       if len(corpus) == 0:
        self.bm25 = None
        return

       self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        if self.bm25 is None:
           return []
        tokenized_query = query.split()

        scores = self.bm25.get_scores(tokenized_query)

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results = []

        for idx in ranked_indices:

            chunk = self.chunks[idx]
            score = float(scores[idx])

            results.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
                "distance": 1 / (score + 1e-6),   # convert score → distance-like
                "modality": "text"
            })

        return results