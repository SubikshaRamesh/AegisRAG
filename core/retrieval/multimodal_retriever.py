from typing import List, Dict
from core.schema.chunk import Chunk
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator


class MultimodalRetriever:
    def __init__(
        self,
        text_faiss: FaissManager,
        image_faiss: ImageFaissManager,
        chunks: List[Chunk]
    ):
        self.text_faiss = text_faiss
        self.image_faiss = image_faiss

        self.text_embedder = EmbeddingGenerator()
        self.clip_embedder = CLIPEmbeddingGenerator()

        # chunk_id → Chunk
        self.chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:

        # 1️⃣ Text search
        text_query_embedding = self.text_embedder.embed([query])
        text_results = self.text_faiss.search(text_query_embedding, top_k)

        # 2️⃣ Image search (CLIP)
        image_query_embedding = self.clip_embedder.embed_text([query])
        image_results = self.image_faiss.search(
            image_query_embedding.astype("float32"),
            top_k
        )

        # 3️⃣ Merge results
        combined = text_results + image_results

        # Sort by distance (lower = better for L2)
        combined = sorted(combined, key=lambda x: x["distance"])

        retrieved = []
        for r in combined[:top_k]:
            chunk = self.chunk_lookup.get(r["chunk_id"])
            if not chunk:
                continue

            retrieved.append({
                "text": chunk.text,
                "source_file": chunk.source_file,
                "source_type": chunk.source_type,
                "timestamp": chunk.timestamp,
                "distance": r["distance"]
            })

        return retrieved
