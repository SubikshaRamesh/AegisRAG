from core.ingestion.ingestion_manager import ingest
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager


def test_audio_faiss():
    audio_path = r"workspaces\default\uploads\sample.mp3"

    # 1. Ingest audio → chunks
    chunks = ingest(
        file_path=audio_path,
        file_type="audio",
        source_id="sample_audio"
    )

    # 2. Embed chunks
    texts = [chunk.text for chunk in chunks]
    embedder = EmbeddingGenerator()
    embeddings = embedder.embed(texts)

    # 3. Add to FAISS
    faiss_manager = FaissManager(embedding_dim=len(embeddings[0]))
    faiss_manager.add(embeddings, chunks)

    print("FAISS index size:", faiss_manager.index.ntotal)
    print("Stored chunk IDs:", len(faiss_manager.chunk_ids))


if __name__ == "__main__":
    test_audio_faiss()
