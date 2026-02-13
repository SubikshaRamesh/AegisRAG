import os
from typing import List

from core.schema.chunk import Chunk
from core.ingestion.pdf_ingest import ingest_pdf
from core.ingestion.audio_ingest import ingest_audio
from core.ingestion.video_ingest import ingest_video_full
from core.storage.metadata_store import MetadataStore
from core.ingestion.image_ingest import ingest_image


def ingest(file_path: str, file_type: str, source_id: str) -> List[Chunk]:
    """
    Unified ingestion entry point.
    Handles PDF, audio, video.
    Persists chunks to SQLite.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_type = file_type.lower()

    if file_type == "pdf":
        chunks = ingest_pdf(file_path)

    elif file_type == "audio":
        chunks = ingest_audio(file_path, source_id)

    elif file_type == "video":
        chunks = ingest_video_full(file_path)
    
    elif file_type == "image":
        chunks = ingest_image(file_path)

    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    # 🔥 Persist ALL chunks to SQLite (including video_frame)
    db_path = "workspaces/default/storage/metadata/chunks.db"
    store = MetadataStore(db_path)
    store.save_chunks(chunks)

    return chunks
