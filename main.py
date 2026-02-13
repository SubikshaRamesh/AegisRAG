import numpy as np

from core.storage.metadata_store import MetadataStore
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator
from core.pipeline.query_system import QuerySystem


DB_PATH = "workspaces/default/storage/metadata/chunks.db"


def build_multimodal_system():
    print("Loading chunks from SQLite...")
    store = MetadataStore(DB_PATH)
    chunks = store.get_all_chunks()

    if not chunks:
        raise RuntimeError("No chunks found in database.")

    print(f"Loaded {len(chunks)} chunks.")

    # Split by type
    text_chunks = [c for c in chunks if c.source_type != "video_frame"]
    image_chunks = [c for c in chunks if c.source_type in ["video_frame", "image"]]

    print(f"Text chunks: {len(text_chunks)}")
    print(f"Image chunks: {len(image_chunks)}")

    # ----------------------------
    # TEXT FAISS
    # ----------------------------
    text_embedder = EmbeddingGenerator()

    if text_chunks:
        texts = [c.text for c in text_chunks]
        text_embeddings = text_embedder.embed(texts)
        text_embeddings = np.array(text_embeddings).astype("float32")

        text_faiss = FaissManager(embedding_dim=text_embeddings.shape[1])
        text_faiss.add(text_embeddings, text_chunks)
        print("Text FAISS built.")
    else:
        text_faiss = FaissManager(embedding_dim=384)
        print("No text chunks found.")

    # ----------------------------
    # IMAGE FAISS (CLIP)
    # ----------------------------
    image_faiss = ImageFaissManager()

    if image_chunks:
        clip = CLIPEmbeddingGenerator()

        frame_paths = [c.text for c in image_chunks]  # text now stores frame path
        image_embeddings = clip.embed_images(frame_paths)
        image_embeddings = np.array(image_embeddings).astype("float32")

        image_faiss.add(image_embeddings, image_chunks)
        print("Image FAISS built.")
    else:
        print("No image chunks found.")

    # ----------------------------
    # Build Query System
    # ----------------------------
    query_system = QuerySystem(
        text_faiss=text_faiss,
        image_faiss=image_faiss,
        db_path=DB_PATH
    )

    return query_system


if __name__ == "__main__":
    qs = build_multimodal_system()

    print("\nMultimodal RAG ready.")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("Ask: ")
        if question.lower() == "exit":
            break

        result = qs.query(question, top_k=5)

        print("\nANSWER:\n")
        print(result["answer"])

        print("\nCITATIONS:\n")
        for c in result["citations"]:
            print(c)

        print("\n" + "-" * 60 + "\n")
