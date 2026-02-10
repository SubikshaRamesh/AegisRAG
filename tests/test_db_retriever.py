import numpy as np

from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.storage.metadata_store import MetadataStore
from core.retrieval.db_retriever import DBRetriever

DB_PATH = "workspaces/default/storage/metadata/chunks.db"


def main():
    print("=== DB RETRIEVER TEST STARTED ===")

    # 1. Load chunks from SQLite (SINGLE SOURCE OF TRUTH)
    store = MetadataStore(DB_PATH)
    chunks = store.get_all_chunks()
    print(f"Loaded {len(chunks)} chunks from SQLite")

    if not chunks:
        raise RuntimeError("No chunks found in SQLite DB")

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

    results = retriever.retrieve(query_embedding, top_k=3)

    print("\nDB RETRIEVER RESULTS:\n")
    for r in results:
        print("Source:", r["source_file"], "| Page:", r["page_number"])
        print("Distance:", r["distance"])
        print(r["text"][:300])
        print("-" * 50)

    print("=== DB RETRIEVER TEST FINISHED ===")


if __name__ == "__main__":
    main()
