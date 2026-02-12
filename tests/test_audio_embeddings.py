from core.ingestion.ingestion_manager import ingest
from core.embeddings.embedder import EmbeddingGenerator


def test_audio_embeddings():
    audio_path = r"workspaces\default\uploads\sample.mp3"

    chunks = ingest(
        file_path=audio_path,
        file_type="audio",
        source_id="sample_audio"
    )

    texts = [chunk.text for chunk in chunks]

    embedder = EmbeddingGenerator()
    embeddings = embedder.embed(texts)

    print("Number of chunks:", len(chunks))
    print("Number of embeddings:", len(embeddings))
    print("Embedding dimension:", len(embeddings[0]))


if __name__ == "__main__":
    test_audio_embeddings()
