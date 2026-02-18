from typing import List, Dict
from core.schema.chunk import Chunk
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss import ImageFaissManager
from core.logger import get_logger

logger = get_logger(__name__)


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

        logger.info("[DEBUG RETRIEVAL] --- RETRIEVER DEBUG START ---")
        logger.info(f"[DEBUG RETRIEVAL] Chunk lookup size: {len(self.chunk_lookup)} chunks")
        
        # 1️⃣ Search text FAISS
        logger.info("[DEBUG RETRIEVAL] Searching text FAISS...")
        text_results = self.text_faiss.search(text_query_embedding, top_k)
        logger.info(f"[DEBUG RETRIEVAL] Text FAISS returned {len(text_results)} results")

        # 2️⃣ Search image FAISS
        logger.info("[DEBUG RETRIEVAL] Searching image FAISS...")
        image_results = self.image_faiss.search(image_query_embedding, top_k)
        logger.info(f"[DEBUG RETRIEVAL] Image FAISS returned {len(image_results)} results")

        # 3️⃣ Combine results
        combined = text_results + image_results
        logger.info(f"[DEBUG RETRIEVAL] Combined results: {len(combined)} total")

        # If nothing relevant found
        if not combined:
            logger.warning("[DEBUG RETRIEVAL] NO RESULTS from FAISS search")
            return []

        # 4️⃣ Sort by L2 distance (smaller is better)
        combined = sorted(combined, key=lambda x: x["distance"])
        logger.info(f"[DEBUG RETRIEVAL] Sorted {len(combined)} results by distance")

        retrieved = []
        modality_count = {}

        # 5️⃣ Diversity control (max 2 per modality)
        for i, result in enumerate(combined):
            chunk_id = result["chunk_id"]
            logger.info(f"[DEBUG RETRIEVAL] Processing result {i+1}: chunk_id={chunk_id[:20]}... distance={result['distance']:.4f}")
            
            chunk = self.chunk_lookup.get(chunk_id)
            if not chunk:
                logger.warning(f"[DEBUG RETRIEVAL] ✗ Chunk NOT found in lookup: {chunk_id}")
                continue
            
            logger.info(f"[DEBUG RETRIEVAL] ✓ Chunk found in lookup")

            modality = getattr(chunk, "modality", "unknown")
            logger.info(f"[DEBUG RETRIEVAL] Modality: {modality}, count so far: {modality_count.get(modality, 0)}")

            if modality_count.get(modality, 0) >= 2:
                logger.info(f"[DEBUG RETRIEVAL] ✗ Filtering: {modality} already has 2 results")
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
            logger.info(f"[DEBUG RETRIEVAL] ✓ Added to retrieved (total: {len(retrieved)})")

            if len(retrieved) >= top_k:
                logger.info(f"[DEBUG RETRIEVAL] Reached top_k limit ({top_k})")
                break

        logger.info(f"[DEBUG RETRIEVAL] Final retrieved count: {len(retrieved)}")
        logger.info("[DEBUG RETRIEVAL] --- RETRIEVER DEBUG END ---")
        return retrieved
