from typing import List, Dict, Optional, Tuple, Iterator
import numpy as np
import time
import os

from core.retrieval.reranker import CrossEncoderReranker
from core.retrieval.bm25_retriever import BM25Retriever
from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.schema.chunk import Chunk
from core.llm.generator import OfflineLLM
from core.storage.metadata_store import MetadataStore
from core.logger import get_logger

logger = get_logger(__name__)

MULTIMODAL_KEYWORDS = {
    "image", "picture", "photo", "screenshot",
    "video", "frame", "audio", "sound"
}

SUMMARY_KEYWORDS = {
    "summarize",
    "summary",
    "summarise",
    "overview",
    "brief",
    "explain the document",
    "give summary",
    "summarize the documents"
}

MAX_DISTANCE = 5.0
MAX_CONTEXT_CHARS = 5000
CONFIDENCE_THRESHOLD = 35
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md"}
AUDIO_EXTENSIONS = {".wav", ".mp3"}


class QuerySystem:
    """Production-ready Multimodal Offline RAG System"""

    def __init__(
        self,
        text_faiss: FaissManager,
        image_faiss: ImageFaissManager,
        db_path: str = "workspaces/default/storage/metadata/chunks.db",
        model_path: str = "models/Phi-3-mini-4k-instruct-q4.gguf",
    ):

        logger.info("[INIT] Creating QuerySystem...")

        self.text_embedder = EmbeddingGenerator()
        self.clip_embedder = CLIPEmbeddingGenerator()

        self.text_faiss = text_faiss
        self.image_faiss = image_faiss

        self.llm = OfflineLLM(model_path=model_path)
        self.store = MetadataStore(db_path)

        # Hybrid retrieval
        self.bm25 = BM25Retriever(self.store)

        # Cross encoder reranker
        self.reranker = CrossEncoderReranker()

        logger.info(f"[FAISS] Text index chunks: {len(self.text_faiss.chunk_ids)}")
        logger.info(f"[FAISS] Image index chunks: {len(self.image_faiss.chunk_ids)}")

        logger.info("[INIT] QuerySystem initialized")

    # =====================================================
    # NORMALIZE DISTANCE SCORES
    # =====================================================

    def _normalize(self, results: List[Dict]) -> List[Dict]:

        if not results:
            return results

        distances = [r["distance"] for r in results]

        min_d = min(distances)
        max_d = max(distances)

        if max_d == min_d:
            for r in results:
                r["norm_score"] = 0
            return results

        for r in results:
            r["norm_score"] = (r["distance"] - min_d) / (max_d - min_d)

        return results

    # =====================================================
    # MULTI DOCUMENT CHUNK SELECTION
    # =====================================================

    def _select_diverse_chunks(self, results: List[Dict], max_chunks: int = 8) -> List[Dict]:

        selected = []
        seen_files = set()

        for r in results:

            source_file = r.get("source_file")

            if source_file not in seen_files:
                selected.append(r)
                seen_files.add(source_file)

            elif len(selected) < max_chunks:
                selected.append(r)

            if len(selected) >= max_chunks:
                break

        return selected

    # =====================================================
    # MERGE RESULTS (FAISS + BM25 + IMAGE)
    # =====================================================

    def _merge_results(self, *result_lists):

        k = 60
        scores = {}
        metadata = {}

        for results in result_lists:
            for rank, r in enumerate(results):

                cid = r["chunk_id"]

                rrf = 1 / (k + rank+1)

                if cid not in scores:
                    scores[cid] = 0
                    metadata[cid] = r

                scores[cid] += rrf

        merged = []

        for cid, score in scores.items():

            item = metadata[cid]
            item["rrf_score"] = score

            merged.append(item)

        merged.sort(key=lambda x: x["rrf_score"], reverse=True)

        return merged

    # =====================================================
    # MAIN QUERY
    # =====================================================

    def query(
        self,
        question: str,
        top_k: int = 8,
        history_messages: Optional[List[Dict]] = None,
    ) -> Dict:

        query_start = time.time()

        logger.info(f"[QUERY] START - {question[:80]}")

        question_lower = question.lower()

        is_summary_query = any(k in question_lower for k in SUMMARY_KEYWORDS)

        if is_summary_query:
            top_k = 15

        # ================= EMBEDDING =================

        text_embedding = self.text_embedder.embed([question])
        text_embedding = np.array(text_embedding).astype("float32")

        # ================= TEXT FAISS =================

        text_results = self.text_faiss.search(text_embedding, top_k=top_k)

        # ================= BM25 =================

        bm25_results = self.bm25.search(question, top_k=top_k)

        # ================= IMAGE FAISS =================

        image_results = []

        enable_multimodal = any(k in question_lower for k in MULTIMODAL_KEYWORDS)

        if enable_multimodal and len(self.image_faiss.chunk_ids) > 0:

            image_embedding = self.clip_embedder.embed_text([question])
            image_embedding = np.array(image_embedding).astype("float32")

            image_results = self.image_faiss.search(image_embedding, top_k=top_k)

        # ================= MERGE =================

        combined = self._merge_results(text_results, bm25_results, image_results)

        logger.info(f"[RETRIEVAL] FAISS results: {len(text_results)}")
        logger.info(f"[RETRIEVAL] BM25 results: {len(bm25_results)}")
        logger.info(f"[RETRIEVAL] Image results: {len(image_results)}")
        logger.info(f"[RETRIEVAL] Combined results: {len(combined)}")

        combined = self._normalize(combined)

        combined = sorted(combined, key=lambda x: x["norm_score"])

        if not combined:

            return {
                "answer": "Information not found in knowledge base.",
                "sources": [],
                "confidence": 0
            }

        # ================= VALIDATE =================

        validated = [r for r in combined if r["distance"] <= MAX_DISTANCE]

        if not validated:

            return {
                "answer": "Insufficient evidence in knowledge base.",
                "sources": [],
                "confidence": 0
            }

        # ================= RERANK =================

        candidates = self._select_diverse_chunks(validated, max_chunks=20)

        selected = self.reranker.rerank(question, candidates, top_k=top_k)
        logger.info(f"[RERANK] Selected chunks: {len(selected)}")

        chunk_ids = [r["chunk_id"] for r in selected]
        distances = [r["distance"] for r in selected]

        # ================= FETCH CHUNKS =================

        chunks = self._fetch_chunks_from_db(chunk_ids)

        if not chunks:
            return {
                "answer": "Information not found in knowledge base.",
                "sources": [],
                "confidence": 0
            }

        # ================= BUILD CONTEXT =================

        contexts = self._build_context(chunks)

        # ================= CONFIDENCE =================

        avg_distance = sum(distances) / len(distances)

        similarity_score = max(0, 1 - (avg_distance / 2))
        coverage_score = min(len(selected) / top_k, 1)

        confidence = round(
            (similarity_score * 0.7 + coverage_score * 0.3) * 100,
            2
        )

        if confidence < CONFIDENCE_THRESHOLD:
            return {
                "answer": "Insufficient evidence in knowledge base.",
                "sources": [],
                "confidence": confidence
            }

        # ================= LLM ANSWER =================

        if is_summary_query:
            question = "Summarize the following documents and explain the key information."

        answer = self.llm.generate_answer(
            question,
            contexts,
            history_messages or []
        )

        # ================= SOURCES =================

        score_map = {r["chunk_id"]: r for r in selected}

        sources_dict = {}

        for chunk in chunks:

            if chunk.source_file not in sources_dict:

                score_data = score_map.get(chunk.chunk_id, {})
                source_type = self._classify_source_type(
                    chunk.source_file,
                    chunk.source_type,
                )

                sources_dict[chunk.source_file] = {
                    "source": chunk.source_file,
                    "type": source_type,
                    "source_type": source_type,
                    "source_file": chunk.source_file,
                    "page_number": chunk.page_number,
                    "timestamp": chunk.timestamp,
                    "score": score_data.get("rerank_score") or score_data.get("retrieval_score") or 0,
                    "retrieval_score": score_data.get("retrieval_score"),
                    "rerank_score": score_data.get("rerank_score"),
                    "confidence": confidence
                }

        sources = sorted(
            sources_dict.values(),
            key=lambda s: (
                self._source_priority(s.get("source_type", "unknown")),
                -(s.get("rerank_score") or 0),
                s.get("source_file", ""),
            ),
        )

        total_time = time.time() - query_start

        logger.info(
            f"[QUERY] COMPLETE in {total_time:.3f}s | Confidence: {confidence}%"
        )

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "chunk_ids": chunk_ids
        }

    # =====================================================
    # STREAMING QUERY
    # =====================================================

    def stream_query(
        self,
        question: str,
        top_k: int = 8,
        history_messages: Optional[List[Dict]] = None,
    ) -> Tuple[Dict, Iterator[str]]:

        result = self.query(question, top_k, history_messages)

        if result["confidence"] == 0:

            metadata = {
                "sources": [],
                "confidence": 0,
                "retrieval_time": 0
            }

            return metadata, iter(["Insufficient evidence in knowledge base."])

        chunks = self._fetch_chunks_from_db(result["chunk_ids"])
        contexts = self._build_context(chunks)

        token_gen = self.llm.stream_answer(
            question,
            contexts,
            history_messages or []
        )

        metadata = {
            "sources": result["sources"],
            "confidence": result["confidence"],
            "retrieval_time": 0
        }

        return metadata, token_gen

    # =====================================================
    # HELPERS
    # =====================================================

    def _fetch_chunks_from_db(self, chunk_ids: List[str]) -> List[Chunk]:

        return [
            self.store.get_chunk(cid)
            for cid in chunk_ids
            if self.store.get_chunk(cid)
        ]

    def _build_context(self, chunks: List[Chunk]) -> List[Dict]:

        contexts = []

        current_chars = 0

        for chunk in chunks:

            remaining = MAX_CONTEXT_CHARS - current_chars

            if remaining <= 0:
                break

            trimmed_text = chunk.text[:remaining]

            contexts.append({
                "text": f"[Source: {chunk.source_file} | Page: {chunk.page_number}]\n{trimmed_text}",
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
            })

            current_chars += len(trimmed_text)

        return contexts

    def _classify_source_type(self, source_file: Optional[str], fallback_type: Optional[str]) -> str:

        ext = os.path.splitext(source_file or "")[1].lower()

        if ext in DOCUMENT_EXTENSIONS:
            return "document"

        if ext in AUDIO_EXTENSIONS:
            return "audio transcript"

        if fallback_type:
            return fallback_type

        return "unknown"

    def _source_priority(self, source_type: str) -> int:

        if source_type == "document":
            return 0

        if source_type == "audio transcript":
            return 1

        return 2