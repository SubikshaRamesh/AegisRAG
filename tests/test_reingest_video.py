from core.ingestion.ingestion_manager import ingest

if __name__ == "__main__":
    video_path = r"workspaces/default/uploads/sample.mp4"

    chunks = ingest(
        file_path=video_path,
        file_type="video",
        source_id="sample_video"
    )

    print("Total chunks stored:", len(chunks))

    video_chunks = [c for c in chunks if c.source_type == "video"]
    frame_chunks = [c for c in chunks if c.source_type == "video_frame"]

    print("Transcript chunks:", len(video_chunks))
    print("Frame chunks:", len(frame_chunks))
from core.storage.metadata_store import MetadataStore

store = MetadataStore("workspaces/default/storage/metadata/chunks.db")
all_chunks = store.get_all_chunks()

print("Total chunks in DB:", len(all_chunks))

video_frames = [c for c in all_chunks if c.source_type == "video_frame"]
print("Frame chunks in DB:", len(video_frames))
