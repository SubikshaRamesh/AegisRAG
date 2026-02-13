from core.embeddings.clip_embedder import CLIPEmbeddingGenerator

if __name__ == "__main__":
    clip = CLIPEmbeddingGenerator()

    image_path = "temp_video_frames/frame_0001.jpg"
    embeddings = clip.embed_images([image_path])

    print("Embedding length:", len(embeddings[0]))
