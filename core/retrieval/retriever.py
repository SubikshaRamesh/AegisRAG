from typing import List, Dict
from core.schema.chunk import Chunk
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss import ImageFaissManager


class Retriever:
    def __init__(
        self,
        text_faiss: FaissManager,
        image_faiss: ImageFaissManager,
        chunks: List[Chunk]
    ):
        """
        text_faiss  → MiniLM embeddings (PDF, DOCX, Audio transcript, Video transcript, Image captions)
        image_faiss → CLIP embeddings (Image visuals, Video frames)
        """
        self.text_faiss = text_faiss
        self.image_faiss = image_faiss

        # Map chunk_id → Chunk object
        self.chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}

    def retrieve(
        self,
        text_query_embedding,
        image_query_embedding,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Perform multimodal retrieval.
        Returns top relevant chunks across all formats.
        """

        # 1️⃣ Search text FAISS
        text_results = self.text_faiss.search(text_query_embedding, top_k)

        # 2️⃣ Search image FAISS
        image_results = self.image_faiss.search(image_query_embedding, top_k)

        # 3️⃣ Combine results
        combined = text_results + image_results

        # If nothing relevant found
        if not combined:
            return []

        # 4️⃣ Sort by L2 distance (smaller is better)
        combined = sorted(combined, key=lambda x: x["distance"])

        retrieved = []
        modality_count = {}

        # 5️⃣ Diversity control (max 2 per modality)
        for result in combined:
            chunk = self.chunk_lookup.get(result["chunk_id"])
            if not chunk:
                continue

            modality = getattr(chunk, "modality", "unknown")

            if modality_count.get(modality, 0) >= 2:
                continue

            retrieved.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "source_file": chunk.source_file,
                "page_number": getattr(chunk, "page_number", None),
                "timestamp_start": getattr(chunk, "timestamp_start", None),
                "timestamp_end": getattr(chunk, "timestamp_end", None),
                "distance": result["distance"],
                "modality": modality
            })

            modality_count[modality] = modality_count.get(modality, 0) + 1

            if len(retrieved) >= top_k:
                break

        return retrieved
