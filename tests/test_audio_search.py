from core.ingestion.ingestion_manager import ingest
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager


def test_audio_search():
    audio_path = r"workspaces\default\uploads\sample.mp3"

    # 1️⃣ Ingest audio
    chunks = ingest(
        file_path=audio_path,
        file_type="audio",
        source_id="sample_audio"
    )

    # 2️⃣ Embed chunks
    texts = [chunk.text for chunk in chunks]
    embedder = EmbeddingGenerator()
    embeddings = embedder.embed(texts)

    # 3️⃣ Index in FAISS
    faiss_manager = FaissManager(embedding_dim=len(embeddings[0]))
    faiss_manager.add(embeddings, chunks)

    # 4️⃣ Ask a question
    query = "What is the moon?"
    query_embedding = embedder.embed([query])

    # 5️⃣ Search
    results = faiss_manager.search(query_embedding, top_k=3)

    print("Query:", query)
    print("\nTop results with content:\n")

    # Create lookup dictionary
    chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}

    for res in results:
        chunk = chunk_lookup.get(res["chunk_id"])

        print("Distance:", res["distance"])
        print("Timestamp:", chunk.timestamp)
        print("Text preview:", chunk.text[:200])
        print("-" * 50)


if __name__ == "__main__":
    test_audio_search()
