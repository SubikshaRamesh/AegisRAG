"""
Verify duplicate protection: ingest same PDF twice, FAISS count should stay the same.

Usage:
  1. Run this script (it will delete, ingest twice, verify)
  2. Or run steps manually (see docstring at top of ingestion_manager)
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAISS_INDEX = "workspaces/default/storage/metadata/faiss.index"
CHUNK_IDS_PKL = "workspaces/default/storage/metadata/chunk_ids.pkl"
CHUNKS_DB = "workspaces/default/storage/metadata/chunks.db"
PDF_PATH = "workspaces/default/uploads/sample.pdf"


def delete_if_exists(*paths):
    for p in paths:
        if os.path.exists(p):
            os.remove(p)
            print(f"  Deleted: {p}")
        else:
            print(f"  (not found): {p}")


def main():
    from core.ingestion.ingestion_manager import ingest
    from core.vector_store.faiss_manager import FaissManager

    FAISS_INDEX_PATH = "workspaces/default/storage/metadata/faiss.index"
    FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/chunk_ids.pkl"
    EMBEDDING_DIM = 384

    print("=== STEP 0: Clean reset ===\n")
    delete_if_exists(FAISS_INDEX, CHUNK_IDS_PKL, CHUNKS_DB)
    print()

    print("=== STEP 1: First ingestion ===\n")
    chunks1 = ingest(PDF_PATH, "pdf", "sample")
    print(f"Ingested {len(chunks1)} chunks.\n")

    print("=== STEP 2: Verify FAISS count (1st time) ===\n")
    fm = FaissManager(embedding_dim=EMBEDDING_DIM, index_path=FAISS_INDEX_PATH, meta_path=FAISS_CHUNK_IDS_PATH)
    n1 = fm.index.ntotal
    print(f"index.ntotal:     {n1}")
    print(f"len(chunk_ids):   {len(fm.chunk_ids)}")
    sample_ids_1 = list(fm.chunk_ids)[:3]
    print(f"Sample chunk_ids: {sample_ids_1}\n")

    print("=== STEP 3: Second ingestion (same file) ===\n")
    chunks2 = ingest(PDF_PATH, "pdf", "sample")
    print(f"Ingested {len(chunks2)} chunks.\n")

    print("=== STEP 4: Verify FAISS count (2nd time) ===\n")
    fm2 = FaissManager(embedding_dim=EMBEDDING_DIM, index_path=FAISS_INDEX_PATH, meta_path=FAISS_CHUNK_IDS_PATH)
    n2 = fm2.index.ntotal
    print(f"index.ntotal:     {n2}")
    print(f"len(chunk_ids):   {len(fm2.chunk_ids)}")
    sample_ids_2 = list(fm2.chunk_ids)[:3]
    print(f"Sample chunk_ids: {sample_ids_2}\n")

    print("=== RESULT ===\n")
    if n2 == n1 and n1 > 0:
        print("SUCCESS: Duplicate protection worked. Count unchanged.")
    elif n2 > n1:
        print("FAIL: Count increased! Duplicate protection failed.")
        print("\nDebug: Compare chunk_ids from first vs second extraction:")
        sample_from_chunks2 = [c.chunk_id for c in chunks2][:3]
        print(f"  From chunks (2nd ingest): {sample_from_chunks2}")
        print(f"  From FAISS (after 1st):   {sample_ids_1}")
        if sample_from_chunks2 != sample_ids_1:
            print("\n  → Chunk IDs differ between runs. Check pdf_ingest determinism.")
    else:
        print("No chunks in index. Check ingestion and FAISS save.")


if __name__ == "__main__":
    main()
