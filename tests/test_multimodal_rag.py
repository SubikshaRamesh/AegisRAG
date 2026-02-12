from core.ingestion.ingestion_manager import ingest
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.storage.metadata_store import MetadataStore
from core.pipeline.query_system import QuerySystem


def test_multimodal_rag():

    # 1️⃣ Ingest PDF
    pdf_chunks = ingest(
        file_path="workspaces/default/uploads/sample.pdf",
        file_type="pdf",
        source_id="sample.pdf"
    )

    # 2️⃣ Ingest Audio
    audio_chunks = ingest(
        file_path="workspaces/default/uploads/sample.mp3",
        file_type="audio",
        source_id="sample.mp3"
    )

    all_chunks = pdf_chunks + audio_chunks

    print(f"Total chunks: {len(all_chunks)}")

    # 3️⃣ Save to SQLite
    store = MetadataStore("workspaces/default/storage/metadata/chunks.db")
    store.save_chunks(all_chunks)

    # 4️⃣ Generate embeddings
    embedder = EmbeddingGenerator()
    texts = [chunk.text for chunk in all_chunks]
    embeddings = embedder.embed(texts)

    # 5️⃣ Build FAISS
    faiss_manager = FaissManager(embedding_dim=embeddings.shape[1])
    faiss_manager.add(embeddings, all_chunks)

    # 6️⃣ Query
    query_system = QuerySystem(faiss_manager)

    response = query_system.query("What is the moon?")

    print("\nANSWER:\n")
    print(response["answer"])

    print("\nCITATIONS:\n")
    for citation in response["citations"]:
        print(citation)


if __name__ == "__main__":
    test_multimodal_rag()
