from core.ingestion.video_ingest import ingest_video_full, prepare_image_embeddings
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.embeddings.embedder import EmbeddingGenerator
from core.retrieval.multimodal_retriever import MultimodalRetriever
import numpy as np


if __name__ == "__main__":
    video_path = r"workspaces/default/uploads/sample.mp4"

    # 1️⃣ Ingest full video (audio + frames)
    chunks = ingest_video_full(video_path)

    # Split text vs image chunks
    text_chunks = [c for c in chunks if c.source_type == "video"]
    image_chunks = [c for c in chunks if c.source_type == "video_frame"]

    print("Text chunks:", len(text_chunks))
    print("Image chunks:", len(image_chunks))

    # 2️⃣ TEXT FAISS
    text_embedder = EmbeddingGenerator()
    text_embeddings = text_embedder.embed([c.text for c in text_chunks])

    text_faiss = FaissManager(embedding_dim=text_embeddings.shape[1])
    text_faiss.add(text_embeddings.astype("float32"), text_chunks)

    print("Text FAISS built.")

    # 3️⃣ IMAGE FAISS
    image_embeddings = prepare_image_embeddings(image_chunks)

    image_faiss = ImageFaissManager()
    image_faiss.add(image_embeddings, image_chunks)

    print("Image FAISS built.")

    # 4️⃣ Multimodal Retrieval
    retriever = MultimodalRetriever(
        text_faiss=text_faiss,
        image_faiss=image_faiss,
        chunks=chunks
    )

    results = retriever.retrieve("moon in the sky", top_k=5)

    print("\nTop Multimodal Results:")
    for r in results:
        print(r)
