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

    Text (MiniLM) → Text FAISS (384-dim)
    Image (CLIP)  → Image FAISS (512-dim)

    Results merged → SQLite fetch → LLM answer generation.
    """

    def __init__(
        self,
        text_faiss: FaissManager,
        image_faiss: ImageFaissManager,
        db_path: str = "workspaces/default/storage/metadata/chunks.db",
        model_path: str = "models/mistral.gguf",
    ):
        # Embedders
        self.text_embedder = EmbeddingGenerator()
        self.clip_embedder = CLIPEmbeddingGenerator()

        # Dual FAISS indexes
        self.text_faiss = text_faiss
        self.image_faiss = image_faiss

        # LLM
        self.llm = OfflineLLM(model_path=model_path)

        # SQLite metadata store
        self.store = MetadataStore(db_path)

    def query(self, question: str, top_k: int = 5) -> Dict:
        """
        Full multimodal RAG pipeline:
        1. Embed question (text + CLIP)
        2. Search both FAISS indexes
        3. Merge & deduplicate chunk IDs
        4. Fetch chunks from SQLite
        5. Build LLM context
        6. Generate answer
        7. Return answer + citations
        """

        # ----------------------------
        # 1️⃣ TEXT SEARCH (MiniLM)
        # ----------------------------
        text_query_embedding = self.text_embedder.embed([question])
        text_query_embedding = np.array(text_query_embedding).astype("float32")

        text_results = self.text_faiss.search(
            text_query_embedding,
            top_k=top_k
        )

        # ----------------------------
        # 2️⃣ IMAGE SEARCH (CLIP)
        # ----------------------------
        image_results = []

        if len(self.image_faiss.chunk_ids) > 0:
            image_query_embedding = self.clip_embedder.embed_text([question])
            image_query_embedding = np.array(image_query_embedding).astype("float32")

            image_results = self.image_faiss.search(
                image_query_embedding,
                top_k=top_k
            )

        # ----------------------------
        # 3️⃣ MERGE RESULTS
        # ----------------------------
        combined = text_results + image_results
        combined = sorted(combined, key=lambda x: x["distance"])

        # Deduplicate chunk IDs while preserving order
        chunk_ids: List[str] = []

        for result in combined:
            cid = result["chunk_id"]
            if cid not in chunk_ids:
                chunk_ids.append(cid)

            if len(chunk_ids) >= top_k:
                break

        # ----------------------------
        # 4️⃣ FETCH CHUNKS FROM DB
        # ----------------------------
        retrieved_chunks = self._fetch_chunks_from_db(chunk_ids)

        # ----------------------------
        # 5️⃣ BUILD CLEAN CONTEXT
        # ----------------------------
        contexts = self._build_context(retrieved_chunks)

        # ----------------------------
        # 6️⃣ GENERATE ANSWER
        # ----------------------------
        answer = self.llm.generate_answer(question, contexts)

        # ----------------------------
        # 7️⃣ PREPARE CITATIONS
        # ----------------------------
        seen = set()
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
            "citations": citations
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
    # Build clean LLM context
    # --------------------------------------------------
    def _build_context(self, chunks: List[Chunk]) -> List[Dict]:
        """
        Build clean LLM context.
        Skip raw image file path chunks.
        """

        contexts: List[Dict] = []

        for chunk in chunks:

            # Skip raw image file path chunks
            if chunk.source_type == "image":
                continue

            contexts.append(
                {
                    "text": chunk.text,
                    "source_file": chunk.source_file,
                    "page_number": chunk.page_number,
                    "timestamp": chunk.timestamp,
                }
            )

        return contexts
