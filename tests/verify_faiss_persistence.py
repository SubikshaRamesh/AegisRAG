"""
Verify FAISS persistence after restart.

Run this script AFTER:
  1. Running ingestion (e.g. ingest a PDF/audio file)
  2. Running main.py (which builds FAISS and calls save())

Then RESTART Python (close and reopen terminal/IDE) and run this script
to confirm index.ntotal and len(chunk_ids) match the ingested count.
"""

from core.vector_store.faiss_manager import FaissManager

FAISS_INDEX_PATH = "workspaces/default/storage/metadata/faiss.index"
FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/chunk_ids.pkl"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 produces 384-dim vectors


def main():
    print("=== FAISS PERSISTENCE VERIFICATION ===\n")

    faiss_manager = FaissManager(
        embedding_dim=EMBEDDING_DIM,
        index_path=FAISS_INDEX_PATH,
        meta_path=FAISS_CHUNK_IDS_PATH,
    )

    ntotal = faiss_manager.index.ntotal
    n_chunk_ids = len(faiss_manager.chunk_ids)

    print(f"index.ntotal:     {ntotal}")
    print(f"len(chunk_ids):   {n_chunk_ids}")
    print()

    if ntotal == n_chunk_ids and ntotal > 0:
        print("SUCCESS: Vectors persisted correctly after restart.")
    elif ntotal == 0 and n_chunk_ids == 0:
        print("No data loaded. Run ingestion + main.py first to build and save FAISS.")
    else:
        print("WARNING: index.ntotal != len(chunk_ids) - possible inconsistency.")


if __name__ == "__main__":
    main()
