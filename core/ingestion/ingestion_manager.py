import os
from typing import List

from core.schema.chunk import Chunk
from core.ingestion.pdf_ingest import ingest_pdf
from core.ingestion.audio_ingest import ingest_audio  # adjust if function name differs
from core.storage.metadata_store import MetadataStore


def ingest(file_path: str, file_type: str, source_id: str) -> List[Chunk]:
    """
    Unified ingestion entry point.
    Handles PDF, audio, etc.
    Persists chunks to SQLite.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_type = file_type.lower()

    if file_type == "pdf":
        chunks = ingest_pdf(file_path)

    elif file_type == "audio":
        chunks = ingest_audio(file_path, source_id)

    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    # 🔥 Persist chunks to SQLite
    db_path = "workspaces/default/storage/metadata/chunks.db"
    store = MetadataStore(db_path)
    store.save_chunks(chunks)

    return chunks
