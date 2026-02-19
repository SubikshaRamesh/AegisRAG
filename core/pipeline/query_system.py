from typing import List, Dict, Optional
import numpy as np
import time

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


class QuerySystem:
    """Smart Multimodal RAG with detailed performance logging."""

    def __init__(
        self,
        text_faiss: FaissManager,
        image_faiss: ImageFaissManager,
        db_path: str = "workspaces/default/storage/metadata/chunks.db",
        model_path: str = "models/Phi-3-mini-4k-instruct-q4.gguf",
    ):
        logger.info("[INIT] Creating QuerySystem...")
        init_start = time.time()
        
        logger.debug("[INIT] Creating EmbeddingGenerator...")
        self.text_embedder = EmbeddingGenerator()
        logger.debug(f"[INIT] EmbeddingGenerator created (ID: {id(self.text_embedder)})")
        
        logger.debug("[INIT] Creating CLIPEmbeddingGenerator...")
        self.clip_embedder = CLIPEmbeddingGenerator()
        logger.debug(f"[INIT] CLIPEmbeddingGenerator created (ID: {id(self.clip_embedder)})")

        self.text_faiss = text_faiss
        self.image_faiss = image_faiss

        logger.debug("[INIT] Creating OfflineLLM...")
        self.llm = OfflineLLM(model_path=model_path)
        logger.debug(f"[INIT] OfflineLLM created (ID: {id(self.llm)})")
        
        logger.debug("[INIT] Creating MetadataStore...")
        self.store = MetadataStore(db_path)
        logger.debug(f"[INIT] MetadataStore created (ID: {id(self.store)})")
        
        init_time = time.time() - init_start
        logger.info(f"[INIT] QuerySystem initialized in {init_time:.3f}s")

    def query(
        self,
        question: str,
        top_k: int = 2,
        history_messages: Optional[List[Dict]] = None,
    ) -> Dict:
        """Execute query with detailed performance logging."""
        query_start = time.time()
        logger.info(f"[QUERY] START - Question: {question[:80]}...")

        # ============ TEXT EMBEDDING ============
        embed_start = time.time()
        text_embedding = self.text_embedder.embed([question])
        text_embedding = np.array(text_embedding).astype("float32")
        embed_time = time.time() - embed_start
        logger.debug(f"[QUERY] Text embedding: {embed_time:.3f}s")

        # ============ TEXT FAISS SEARCH ============
        search_start = time.time()
        text_results = self.text_faiss.search(
            text_embedding,
            top_k=top_k
        )
        search_time = time.time() - search_start
        logger.debug(f"[QUERY] Text FAISS search: {search_time:.3f}s ({len(text_results)} results)")

        # ============ CONDITIONAL IMAGE SEARCH ============
        image_results = []
        image_time = 0

        enable_multimodal = any(k in question.lower() for k in MULTIMODAL_KEYWORDS)
        if enable_multimodal:
            logger.debug(f"[QUERY] Multimodal keywords detected")
            if len(self.image_faiss.chunk_ids) > 0:
                clip_start = time.time()
                image_embedding = self.clip_embedder.embed_text([question])
                image_embedding = np.array(image_embedding).astype("float32")
                clip_time = time.time() - clip_start
                logger.debug(f"[QUERY] CLIP embedding: {clip_time:.3f}s")

                img_search_start = time.time()
                image_results = self.image_faiss.search(
                    image_embedding,
                    top_k=top_k
                )
                image_search_time = time.time() - img_search_start
                image_time = clip_time + image_search_time
                logger.debug(f"[QUERY] Image FAISS search: {image_search_time:.3f}s ({len(image_results)} results)")
            else:
                logger.debug("[QUERY] Multimodal enabled but no image vectors available")
        else:
            logger.debug("[QUERY] No multimodal keywords - skipping image search")

        # ============ COMBINE & RANK ============
        combined = sorted(
            text_results + image_results,
            key=lambda x: x["distance"]
        )
        logger.debug(f"[QUERY] Combined {len(text_results)} text + {len(image_results)} image = {len(combined)} total results")

        if not combined:
            logger.info("[QUERY] No results found - returning fallback")
            return {
                "answer": "Information not found in knowledge base.",
                "sources": [],
                "confidence": 0
            }

        # ============ EXTRACT TOP K ============
        chunk_ids = [r["chunk_id"] for r in combined[:top_k]]
        distances = [r["distance"] for r in combined[:top_k]]
        logger.debug(f"[QUERY] Selected top {len(chunk_ids)} chunks")

        # ============ DATABASE FETCH ============
        db_start = time.time()
        chunks = self._fetch_chunks_from_db(chunk_ids)
        db_time = time.time() - db_start
        logger.debug(f"[QUERY] DB fetch: {db_time:.3f}s ({len(chunks)} chunks)")

        # ============ BUILD CONTEXT ============
        context_start = time.time()
        contexts = self._build_context(chunks)
        context_time = time.time() - context_start
        logger.debug(f"[QUERY] Context build: {context_time:.3f}s ({sum(len(c['text']) for c in contexts)} total chars)")

        # ============ LLM GENERATION ============
        llm_start = time.time()
        answer = self.llm.generate_answer(
            question,
            contexts,
            history_messages or []
        )
        llm_time = time.time() - llm_start
        logger.debug(f"[QUERY] LLM generation: {llm_time:.3f}s")

        # ============ CONFIDENCE ============
        avg_distance = sum(distances) / len(distances)
        similarity = max(0, 1 - (avg_distance / 2))
        confidence = round(similarity * 100, 2)
        logger.debug(f"[QUERY] Confidence: {confidence}%")

        # ============ DEDUPLICATE SOURCES ============
        sources_dict = {}
        for chunk in chunks:
            if chunk.source_file not in sources_dict:
                sources_dict[chunk.source_file] = {
                    "source_type": chunk.source_type,
                    "source_file": chunk.source_file,
                    "score": confidence,
                    "page_number": chunk.page_number,
                    "timestamp": chunk.timestamp,
                }

        # ============ FINAL TIMING ============
        total_query_time = time.time() - query_start
        logger.info(
            f"[QUERY] COMPLETE in {total_query_time:.3f}s | "
            f"Embed: {embed_time:.3f}s | "
            f"TextSearch: {search_time:.3f}s | "
            f"ImageSearch: {image_time:.3f}s | "
            f"DB: {db_time:.3f}s | "
            f"Context: {context_time:.3f}s | "
            f"LLM: {llm_time:.3f}s | "
            f"Confidence: {confidence}%"
        )

        return {
            "answer": answer,
            "sources": list(sources_dict.values()),
            "confidence": confidence
        }

    def stream_query(
        self,
        question: str,
        top_k: int = 2,
        history_messages: Optional[List[Dict]] = None,
    ) -> tuple:
        """Execute query with streaming LLM response.
        
        Returns:
            tuple: (source_metadata dict, token_generator)
            
        The generator yields individual tokens as the LLM generates them.
        The metadata includes sources and confidence for display.
        """
        query_start = time.time()
        logger.info(f"[STREAM QUERY] START - Question: {question[:80]}...")

        # ============ TEXT EMBEDDING ============
        embed_start = time.time()
        text_embedding = self.text_embedder.embed([question])
        text_embedding = np.array(text_embedding).astype("float32")
        embed_time = time.time() - embed_start
        logger.debug(f"[STREAM QUERY] Text embedding: {embed_time:.3f}s")

        # ============ TEXT FAISS SEARCH ============
        search_start = time.time()
        text_results = self.text_faiss.search(
            text_embedding,
            top_k=top_k
        )
        search_time = time.time() - search_start
        logger.debug(f"[STREAM QUERY] Text FAISS search: {search_time:.3f}s ({len(text_results)} results)")

        # ============ CONDITIONAL IMAGE SEARCH ============
        image_results = []
        image_time = 0

        enable_multimodal = any(k in question.lower() for k in MULTIMODAL_KEYWORDS)
        if enable_multimodal:
            logger.debug(f"[STREAM QUERY] Multimodal keywords detected")
            if len(self.image_faiss.chunk_ids) > 0:
                clip_start = time.time()
                image_embedding = self.clip_embedder.embed_text([question])
                image_embedding = np.array(image_embedding).astype("float32")
                clip_time = time.time() - clip_start
                logger.debug(f"[STREAM QUERY] CLIP embedding: {clip_time:.3f}s")

                img_search_start = time.time()
                image_results = self.image_faiss.search(
                    image_embedding,
                    top_k=top_k
                )
                image_search_time = time.time() - img_search_start
                image_time = clip_time + image_search_time
                logger.debug(f"[STREAM QUERY] Image FAISS search: {image_search_time:.3f}s ({len(image_results)} results)")
            else:
                logger.debug("[STREAM QUERY] Multimodal enabled but no image vectors available")
        else:
            logger.debug("[STREAM QUERY] No multimodal keywords - skipping image search")

        # ============ COMBINE & RANK ============
        combined = sorted(
            text_results + image_results,
            key=lambda x: x["distance"]
        )
        logger.debug(f"[STREAM QUERY] Combined {len(text_results)} text + {len(image_results)} image = {len(combined)} total results")

        # ============ EXTRACT TOP K ============
        chunk_ids = [r["chunk_id"] for r in combined[:top_k]]
        distances = [r["distance"] for r in combined[:top_k]]
        logger.debug(f"[STREAM QUERY] Selected top {len(chunk_ids)} chunks")

        # ============ DATABASE FETCH ============
        db_start = time.time()
        chunks = self._fetch_chunks_from_db(chunk_ids)
        db_time = time.time() - db_start
        logger.debug(f"[STREAM QUERY] DB fetch: {db_time:.3f}s ({len(chunks)} chunks)")

        if not chunks:
            logger.info("[STREAM QUERY] No results found - returning fallback")
            metadata = {
                "sources": [],
                "confidence": 0,
                "retrieval_time": time.time() - query_start
            }
            return (metadata, iter(["Information not found in knowledge base."]))

        # ============ BUILD CONTEXT ============
        context_start = time.time()
        contexts = self._build_context(chunks)
        context_time = time.time() - context_start
        logger.debug(f"[STREAM QUERY] Context build: {context_time:.3f}s ({sum(len(c['text']) for c in contexts)} total chars)")

        # ============ CONFIDENCE ============
        avg_distance = sum(distances) / len(distances)
        similarity = max(0, 1 - (avg_distance / 2))
        confidence = round(similarity * 100, 2)
        logger.debug(f"[STREAM QUERY] Confidence: {confidence}%")

        # ============ DEDUPLICATE SOURCES ============
        sources_dict = {}
        for chunk in chunks:
            if chunk.source_file not in sources_dict:
                sources_dict[chunk.source_file] = {
                    "source_type": chunk.source_type,
                    "source_file": chunk.source_file,
                    "score": confidence,
                    "page_number": chunk.page_number,
                    "timestamp": chunk.timestamp,
                }

        # ============ PREPARE STREAMING ============
        retrieval_time = time.time() - query_start
        logger.info(
            f"[STREAM QUERY] Retrieval COMPLETE in {retrieval_time:.3f}s | "
            f"Embed: {embed_time:.3f}s | "
            f"TextSearch: {search_time:.3f}s | "
            f"DB: {db_time:.3f}s | "
            f"Context: {context_time:.3f}s | "
            f"Ready to stream LLM response..."
        )

        # Create generator for streaming LLM
        token_gen = self.llm.stream_answer(
            question,
            contexts,
            history_messages or []
        )

        # Return metadata and generator
        metadata = {
            "sources": list(sources_dict.values()),
            "confidence": confidence,
            "retrieval_time": retrieval_time
        }

        return (metadata, token_gen)

    def _fetch_chunks_from_db(self, chunk_ids: List[str]) -> List[Chunk]:
        return [
            self.store.get_chunk(cid)
            for cid in chunk_ids
            if self.store.get_chunk(cid)
        ]

    def _build_context(self, chunks: List[Chunk]) -> List[Dict]:
        contexts = []

        for chunk in chunks:
            contexts.append({
                "text": chunk.text[:400],   # 🔥 trimmed for speed
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
            })

        return contexts
