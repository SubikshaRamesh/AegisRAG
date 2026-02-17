import os
from typing import List
import numpy as np

from core.schema.chunk import Chunk
from core.ingestion.pdf_ingest import ingest_pdf
from core.ingestion.audio_ingest import ingest_audio
from core.ingestion.video_ingest import ingest_video_full
from core.ingestion.image_ingest import ingest_image
from core.ingestion.document_ingest import ingest_docx
from core.storage.metadata_store import MetadataStore
from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.clip_embedder import CLIPEmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager


FAISS_INDEX_PATH = "workspaces/default/storage/metadata/faiss.index"
FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/chunk_ids.pkl"
IMAGE_FAISS_INDEX_PATH = "workspaces/default/storage/metadata/image_faiss.index"
IMAGE_FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/image_chunk_ids.pkl"
DB_PATH = "workspaces/default/storage/metadata/chunks.db"


def ingest(file_path: str, file_type: str, source_id: str = "") -> List[Chunk]:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_type = file_type.lower()

    # ----------------------------------------
    # STEP 1: Extract Chunks
    # ----------------------------------------
    if file_type == "pdf":
        chunks = ingest_pdf(file_path)

    elif file_type == "audio":
        chunks = ingest_audio(file_path, source_id)

    elif file_type == "video":
        chunks = ingest_video_full(file_path)

    elif file_type == "image":
        chunks = ingest_image(file_path)

    elif file_type == "docx":
        chunks = ingest_docx(file_path)

    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    if not chunks:
        print("No chunks extracted.")
        return []

    print(f"Extracted {len(chunks)} chunks.")

    # ----------------------------------------
    # STEP 2: Save to SQLite
    # ----------------------------------------
    store = MetadataStore(DB_PATH)
    store.save_chunks(chunks)
    print("Saved chunks to SQLite.")

    # ----------------------------------------
    # STEP 3: Initialize FAISS Managers
    # ----------------------------------------
    text_faiss = FaissManager(
        embedding_dim=384,
        index_path=FAISS_INDEX_PATH,
        meta_path=FAISS_CHUNK_IDS_PATH
    )

    image_faiss = ImageFaissManager(
        embedding_dim=512,
        index_path=IMAGE_FAISS_INDEX_PATH,
        meta_path=IMAGE_FAISS_CHUNK_IDS_PATH
    )

    # ----------------------------------------
    # STEP 4: Generate Text Embeddings
    # ----------------------------------------
    text_chunks = [c for c in chunks if c.text]
    if text_chunks:
        embedder = EmbeddingGenerator()
        texts = [c.text for c in text_chunks]
        embeddings = embedder.embed(texts)
        embeddings = np.array(embeddings).astype("float32")

        text_faiss.add(embeddings, text_chunks)
        text_faiss.save()
        print(f"Added {len(text_chunks)} text vectors to FAISS.")

    # ----------------------------------------
    # STEP 5: Generate Image Embeddings (Visual)
    # ----------------------------------------
    image_chunks = [c for c in chunks if c.source_type == "video_frame"]

    if image_chunks:
        clip = CLIPEmbeddingGenerator()
        image_paths = [c.page_number for c in image_chunks]

        embeddings = clip.embed_images(image_paths)
        embeddings = np.array(embeddings).astype("float32")

        image_faiss.add(embeddings, image_chunks)
        image_faiss.save()
        print(f"Added {len(image_chunks)} image vectors to FAISS.")

    return chunks
