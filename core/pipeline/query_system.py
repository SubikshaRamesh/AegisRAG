from typing import List, Dict
import numpy as np

from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.schema.chunk import Chunk
from core.llm.generator import OfflineLLM
from core.storage.metadata_store import MetadataStore


class QuerySystem:
    """
    Multimodal RAG pipeline:
    Text → MiniLM → Text FAISS
    Image/Video → CLIP → Image FAISS
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

    def query(self, question: str, top_k: int = 3) -> Dict:
        """
        Uses top_k=3 for stable retrieval.
        """

        # -------------------------------------------------
        # 1️⃣ TEXT SEARCH
        # -------------------------------------------------
        text_query_embedding = self.text_embedder.embed([question])
        text_query_embedding = np.array(text_query_embedding).astype("float32")

        text_results = self.text_faiss.search(
            text_query_embedding,
            top_k=top_k
        )

        # -------------------------------------------------
        # 2️⃣ IMAGE SEARCH
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
        # 3️⃣ COMBINE
        # -------------------------------------------------
        combined = text_results + image_results

        if not combined:
            return {
                "answer": "Information not found in knowledge base.",
                "citations": [],
                "confidence": 0
            }

        # -------------------------------------------------
        # 4️⃣ KEYWORD-AWARE RE-RANKING
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
        # 5️⃣ DEDUPLICATE + LIMIT
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
        # 6️⃣ FETCH FROM DB
        # -------------------------------------------------
        retrieved_chunks = self._fetch_chunks_from_db(chunk_ids)

        if not retrieved_chunks:
            return {
                "answer": "Information not found in knowledge base.",
                "citations": [],
                "confidence": 0
            }

        # -------------------------------------------------
        # 7️⃣ BUILD CONTEXT
        # -------------------------------------------------
        contexts = self._build_context(retrieved_chunks)

        if not contexts:
            return {
                "answer": "Information not found in knowledge base.",
                "citations": [],
                "confidence": 0
            }

        # -------------------------------------------------
        # 8️⃣ GENERATE ANSWER
        # -------------------------------------------------
        answer = self.llm.generate_answer(question, contexts)

        # -------------------------------------------------
        # 9️⃣ CONFIDENCE (scaled from L2 distance)
        # -------------------------------------------------
        avg_distance = sum(distances) / len(distances)

        similarity = max(0, 1 - (avg_distance / 2))
        confidence = round(similarity * 100, 2)

        # -------------------------------------------------
        # 🔟 CITATIONS
        # -------------------------------------------------
        citations: List[Dict] = []

        for chunk in retrieved_chunks:
            citation = {
                "source_type": chunk.source_type,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
            }

            if citation not in citations:
                citations.append(citation)

        return {
            "answer": answer,
            "citations": citations,
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
