import os

from core.storage.metadata_store import MetadataStore
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager


# ---- Paths (must match ingestion_manager + main.py) ----
DB_PATH = "workspaces/default/storage/metadata/chunks.db"

TEXT_FAISS_INDEX_PATH = "workspaces/default/storage/metadata/faiss.index"
TEXT_FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/chunk_ids.pkl"

IMAGE_FAISS_INDEX_PATH = "workspaces/default/storage/metadata/image_faiss.index"
IMAGE_FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/image_chunk_ids.pkl"


print("=== SYSTEM STATE ===")

# -----------------------------
# Check SQLite
# -----------------------------
store = MetadataStore(DB_PATH)
chunks = store.get_all_chunks()
print("SQLite chunks:", len(chunks))


# -----------------------------
# Check Text FAISS
# -----------------------------
text_faiss = FaissManager(
    embedding_dim=384,
    index_path=TEXT_FAISS_INDEX_PATH,
    meta_path=TEXT_FAISS_CHUNK_IDS_PATH
)

print("Text FAISS vectors:", len(text_faiss.chunk_ids))


# -----------------------------
# Check Image FAISS
# -----------------------------
image_faiss = ImageFaissManager(
    embedding_dim=512,
    index_path=IMAGE_FAISS_INDEX_PATH,
    meta_path=IMAGE_FAISS_CHUNK_IDS_PATH
)

print("Image FAISS vectors:", len(image_faiss.chunk_ids))


# -----------------------------
# Check File Existence
# -----------------------------
print("FAISS files exist:")
print("  Text index+ids:",
      os.path.exists(TEXT_FAISS_INDEX_PATH) and
      os.path.exists(TEXT_FAISS_CHUNK_IDS_PATH))

print("  Image index+ids:",
      os.path.exists(IMAGE_FAISS_INDEX_PATH) and
      os.path.exists(IMAGE_FAISS_CHUNK_IDS_PATH))
