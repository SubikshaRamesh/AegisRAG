import numpy as np

from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.storage.metadata_store import MetadataStore
from core.retrieval.db_retriever import DBRetriever
from core.llm.generator import OfflineLLM

DB_PATH = "workspaces/default/storage/metadata/chunks.db"
MODEL_PATH = "models/mistral.gguf"


def main():
    print("=== OFFLINE DB-RAG TEST STARTED ===")

    # 1. Load chunks from SQLite
    store = MetadataStore(DB_PATH)
    chunks = store.get_all_chunks()
    print(f"Loaded {len(chunks)} chunks from SQLite")

    if not chunks:
        raise RuntimeError("No chunks found in metadata store")

    # 2. Embed chunks
    embedder = EmbeddingGenerator()
    texts = [c.text for c in chunks]
    embeddings = embedder.embed(texts)
    embeddings = np.array(embeddings).astype("float32")

    # 3. Build FAISS index
    faiss_manager = FaissManager(embedding_dim=embeddings.shape[1])
    faiss_manager.add(embeddings, chunks)

    # 4. DB-backed retriever
    retriever = DBRetriever(faiss_manager, store)

    # 5. Query
    question = "Where are the Apollo landing sites?"
    query_embedding = embedder.embed([question])
    query_embedding = np.array(query_embedding).astype("float32")

    contexts = retriever.retrieve(query_embedding, top_k=3)

    print("\nRetrieved contexts:")
    for c in contexts:
        print(f"- {c['source_file']} | Page {c['page_number']}")

    # 6. Offline LLM
    llm = OfflineLLM(MODEL_PATH)
    answer = llm.generate_answer(question, contexts)

    print("\n=== FINAL ANSWER ===\n")
    print(answer)
    print("\n=== OFFLINE DB-RAG TEST FINISHED ===")


if __name__ == "__main__":
    main()
