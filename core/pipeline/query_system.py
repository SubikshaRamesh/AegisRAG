from typing import List, Dict, Optional
import numpy as np

from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.schema.chunk import Chunk
from core.llm.generator import OfflineLLM
from core.storage.metadata_store import MetadataStore
from core.logger import get_logger

logger = get_logger(__name__)


class QuerySystem:
    """
    Multimodal RAG pipeline:
    Text → Multilingual MiniLM (50+ languages) → Text FAISS (384-dim)
    Image/Video → CLIP → Image FAISS (512-dim)
    
    IMPORTANT:
    Embedding model is loaded ONCE at startup and reused for all queries and ingestion.
    This ensures consistency across all vector operations.
    """

    def __init__(
        self,
        text_faiss: FaissManager,
        image_faiss: ImageFaissManager,
        db_path: str = "workspaces/default/storage/metadata/chunks.db",
        model_path: str = "models/Phi-3-mini-4k-instruct-q4.gguf",
    ):
        self.text_embedder = EmbeddingGenerator()
        self.clip_embedder = CLIPEmbeddingGenerator()

        self.text_faiss = text_faiss
        self.image_faiss = image_faiss

        self.llm = OfflineLLM(model_path=model_path)
        self.store = MetadataStore(db_path)

    def query(
        self,
        question: str,
        top_k: int = 3,
        history_messages: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Uses top_k=3 for stable retrieval.
        Supports multilingual queries by embedding the original question directly.
        """

        logger.info(f"[QUERY] Original: {question[:100]}...")

        # -------------------------------------------------
        # 2️⃣ TEXT SEARCH
        # -------------------------------------------------
        text_query_embedding = self.text_embedder.embed([question])
        text_query_embedding = np.array(text_query_embedding).astype("float32")

        text_results = self.text_faiss.search(
            text_query_embedding,
            top_k=top_k
        )

        # -------------------------------------------------
        # 3️⃣ IMAGE SEARCH
        # -------------------------------------------------
        image_results = []

        if len(self.image_faiss.chunk_ids) > 0:
            image_query_embedding = self.clip_embedder.embed_text([question])
            image_query_embedding = np.array(image_query_embedding).astype("float32")

            image_results = self.image_faiss.search(
                image_query_embedding,
                top_k=top_k
            )

        # -------------------------------------------------
        # 4️⃣ COMBINE
        # -------------------------------------------------
        combined = text_results + image_results

        if not combined:
            return {
                "answer": "Information not found in knowledge base.",
                "citations": [],
                "confidence": 0
            }

        # -------------------------------------------------
        # 5️⃣ KEYWORD-AWARE RE-RANKING
        # -------------------------------------------------
        question_lower = question.lower()

        def keyword_score(chunk_id):
            chunk = self.store.get_chunk(chunk_id)
            if not chunk or not chunk.text:
                return 0
            text_lower = chunk.text.lower()
            score = 0
            for word in question_lower.split():
                if word in text_lower:
                    score += 1
            return score

        combined = sorted(
            combined,
            key=lambda x: (
                keyword_score(x["chunk_id"]),
                -x["distance"]
            ),
            reverse=True
        )

        # -------------------------------------------------
        # 6️⃣ DEDUPLICATE + LIMIT
        # -------------------------------------------------
        chunk_ids: List[str] = []
        distances: List[float] = []

        for result in combined:
            cid = result["chunk_id"]

            if cid not in chunk_ids:
                chunk_ids.append(cid)
                distances.append(result["distance"])

            if len(chunk_ids) >= top_k:
                break

        # -------------------------------------------------
        # 7️⃣ FETCH FROM DB
        # -------------------------------------------------
        retrieved_chunks = self._fetch_chunks_from_db(chunk_ids)

        if not retrieved_chunks:
            return {
                "answer": "Information not found in knowledge base.",
                "citations": [],
                "confidence": 0
            }

        # -------------------------------------------------
        # 8️⃣ BUILD CONTEXT
        # -------------------------------------------------
        contexts = self._build_context(retrieved_chunks)

        if not contexts:
            return {
                "answer": "Information not found in knowledge base.",
                "citations": [],
                "confidence": 0
            }

        # -------------------------------------------------
        # 9️⃣ GENERATE ANSWER
        # -------------------------------------------------
        answer = self.llm.generate_answer(question, contexts, history_messages or [])

        # -------------------------------------------------
        # 🔟 CHECK IF ANSWER WAS FOUND (UX Improvement)
        # -------------------------------------------------
        # When LLM returns "not found" message, clear citations and confidence.
        # This improves UX by not showing confusing retrieved citations when
        # the system explicitly states the answer is not in the knowledge base.
        answer_not_found = (
            "Information not found in knowledge base" in answer
            or "Not found in the provided documents" in answer
        )

        if answer_not_found:
            logger.info("Answer not found in knowledge base - clearing citations")
            return {
                "answer": answer,
                "citations": [],  # No citations when answer not found
                "confidence": 0     # Zero confidence when answer not found
            }

        # -------------------------------------------------
        # 1️⃣1️⃣ CONFIDENCE (scaled from L2 distance)
        # -------------------------------------------------
        avg_distance = sum(distances) / len(distances)

        similarity = max(0, 1 - (avg_distance / 2))
        confidence = round(similarity * 100, 2)

        # -------------------------------------------------
        # 1️⃣2️⃣ SOURCES
        # -------------------------------------------------
        distance_by_chunk = {
            chunk_id: distances[idx]
            for idx, chunk_id in enumerate(chunk_ids)
        }

        sources: List[Dict] = []

        for chunk in retrieved_chunks:
            distance = distance_by_chunk.get(chunk.chunk_id, avg_distance)
            similarity = max(0, 1 - (distance / 2))
            score = round(similarity * 100, 2)

            source = {
                "source_type": chunk.source_type,
                "source_file": chunk.source_file,
                "score": score,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
            }

            if source not in sources:
                sources.append(source)

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence
        }

    # --------------------------------------------------
    # Fetch full chunk objects
    # --------------------------------------------------
    def _fetch_chunks_from_db(self, chunk_ids: List[str]) -> List[Chunk]:
        chunks: List[Chunk] = []

        for cid in chunk_ids:
            chunk = self.store.get_chunk(cid)
            if chunk:
                chunks.append(chunk)

        return chunks

    # --------------------------------------------------
    # Build LLM context
    # --------------------------------------------------
    def _build_context(self, chunks: List[Chunk]) -> List[Dict]:

        contexts: List[Dict] = []

        for chunk in chunks:
            contexts.append(
                {
                    "text": chunk.text,
                    "source_file": chunk.source_file,
                    "page_number": chunk.page_number,
                    "timestamp": chunk.timestamp,
                }
            )

        return contexts
