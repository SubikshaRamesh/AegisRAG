from typing import List, Dict
from core.schema.chunk import Chunk
from core.vector_store.faiss_manager import FaissManager


class Retriever:
    def __init__(self, faiss_manager: FaissManager, chunks: List[Chunk]):
        # Map chunk_id → Chunk
        self.chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}
        self.faiss = faiss_manager

    def retrieve(self, query_embedding, top_k: int = 5) -> List[Dict]:
        """
        Retrieve top-k relevant chunks with citation metadata.
        """
        results = self.faiss.search(query_embedding, top_k)

        retrieved = []
        for r in results:
            chunk = self.chunk_lookup.get(r["chunk_id"])
            if not chunk:
                continue

            retrieved.append({
                "text": chunk.text,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "distance": r["distance"]
            })

        return retrieved
