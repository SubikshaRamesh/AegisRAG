from core.ingestion.video_ingest import ingest_video_frames, prepare_image_embeddings
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator

if __name__ == "__main__":
    video_path = r"workspaces/default/uploads/sample.mp4"

    # 1️⃣ Ingest frame chunks
    frame_chunks = ingest_video_frames(video_path, interval_seconds=5)
    image_embeddings = prepare_image_embeddings(frame_chunks)

    # 2️⃣ Create image FAISS
    image_faiss = ImageFaissManager()

    # 3️⃣ Add embeddings
    image_faiss.add(image_embeddings, frame_chunks)

    print("Image FAISS built.")

    # 4️⃣ Embed query using CLIP text encoder
    clip = CLIPEmbeddingGenerator()
    query_embedding = clip.embed_text(["moon in the sky"])

    # 5️⃣ Search image index
    results = image_faiss.search(query_embedding.astype("float32"), top_k=3)

    print("Top image search results:")
    for r in results:
        print(r)
