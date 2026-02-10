from typing import List, Dict
import numpy as np
from core.vector_store.faiss_manager import FaissManager
from core.storage.metadata_store import MetadataStore


class DBRetriever:
    def __init__(self, faiss_manager: FaissManager, metadata_store: MetadataStore):
        self.faiss = faiss_manager
        self.store = metadata_store

    def retrieve(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        Retrieve top-k chunks using FAISS and load metadata from SQLite.
        """
        results = self.faiss.search(query_embedding, top_k)

        retrieved = []
        for r in results:
            chunk = self.store.get_chunk(r["chunk_id"])
            if not chunk:
                continue

            retrieved.append({
                "text": chunk.text,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "distance": r["distance"]
            })

        return retrieved
