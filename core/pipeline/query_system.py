from typing import List, Dict

from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.schema.chunk import Chunk
from core.llm.generator import OfflineLLM
from core.storage.metadata_store import MetadataStore


class QuerySystem:
    """
    Orchestrates embedding → FAISS retrieval → SQLite chunk fetch →
    context construction → LLM answer generation.

    Works for PDF, audio, or any modality stored as Chunk.
    """

    def __init__(
        self,
        faiss_manager: FaissManager,
        db_path: str = "workspaces/default/storage/metadata/chunks.db",
        model_path: str = "models/mistral.gguf",
    ):
        self.embedder = EmbeddingGenerator()
        self.faiss = faiss_manager
        self.llm = OfflineLLM(model_path=model_path)

        # SQLite metadata store
        self.store = MetadataStore(db_path)

    def query(self, question: str, top_k: int = 5) -> Dict:
        """
        Full RAG pipeline:
        1. Embed question
        2. FAISS search
        3. Fetch full chunks from SQLite
        4. Build LLM context
        5. Generate answer
        6. Return answer + citations
        """

        # 1️⃣ Embed question
        query_embedding = self.embedder.embed([question])

        # 2️⃣ Search FAISS
        results = self.faiss.search(query_embedding, top_k=top_k)

        # 3️⃣ Extract chunk IDs
        chunk_ids = [r["chunk_id"] for r in results]

        # 4️⃣ Fetch full chunks from SQLite
        retrieved_chunks = self._fetch_chunks_from_db(chunk_ids)

        # 5️⃣ Build context list for LLM
        contexts = self._build_context(retrieved_chunks)

        # 6️⃣ Generate answer
        answer = self.llm.generate_answer(question, contexts)

        # 7️⃣ Prepare citations
        citations = [
            {
                "source_type": chunk.source_type,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
            }
            for chunk in retrieved_chunks
        ]

        return {
            "answer": answer,
            "citations": citations
        }

    def _fetch_chunks_from_db(self, chunk_ids: List[str]) -> List[Chunk]:
        """
        Fetch full Chunk objects from SQLite using chunk IDs.
        """
        chunks: List[Chunk] = []

        for cid in chunk_ids:
            chunk = self.store.get_chunk(cid)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _build_context(self, chunks: List[Chunk]) -> List[Dict]:
        """
        Convert Chunk objects into the context format expected by OfflineLLM.
        Each context item includes:
        - text
        - source_file
        - page_number
        - timestamp
        """

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
