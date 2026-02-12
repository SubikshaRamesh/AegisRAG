from core.ingestion.ingestion_manager import ingest
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.pipeline.query_system import QuerySystem


def test_full_rag_audio():
    audio_path = r"workspaces\default\uploads\sample.mp3"

    # 1️⃣ Ingest (this now saves to SQLite)
    chunks = ingest(
        file_path=audio_path,
        file_type="audio",
        source_id="sample.mp3"
    )

    # 2️⃣ Embed + index in FAISS
    texts = [chunk.text for chunk in chunks]
    embedder = EmbeddingGenerator()
    embeddings = embedder.embed(texts)

    faiss_manager = FaissManager(embedding_dim=len(embeddings[0]))
    faiss_manager.add(embeddings, chunks)

    # 3️⃣ Create QuerySystem
    qs = QuerySystem(faiss_manager)

    # 4️⃣ Ask question
    result = qs.query("What is the moon?")

    print("\nANSWER:\n")
    print(result["answer"])

    print("\nCITATIONS:\n")
    for c in result["citations"]:
        print(c)


if __name__ == "__main__":
    test_full_rag_audio()
