import time
import os
import platform

from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.pipeline.query_system import QuerySystem


DB_PATH = "workspaces/default/storage/metadata/chunks.db"
FAISS_INDEX_PATH = "workspaces/default/storage/metadata/faiss.index"
FAISS_CHUNK_IDS_PATH = "workspaces/default/storage/metadata/chunk_ids.pkl"

AUTO_OPEN_FRAMES = False


def open_image(path):
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            os.system(f"open '{path}'")
        else:
            os.system(f"xdg-open '{path}'")
    except Exception as e:
        print(f"Could not open image: {e}")


def build_multimodal_system():
    print("Initializing system...")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    # Load existing FAISS indexes (NO ingestion, NO rebuilding)
    text_faiss = FaissManager(
        embedding_dim=384,
        index_path=FAISS_INDEX_PATH,
        meta_path=FAISS_CHUNK_IDS_PATH,
    )

    image_faiss = ImageFaissManager()

    print("System ready.")

    return QuerySystem(
        text_faiss=text_faiss,
        image_faiss=image_faiss,
        db_path=DB_PATH
    )


if __name__ == "__main__":
    qs = build_multimodal_system()

    print("\nMultimodal RAG ready.")
    print("Commands:")
    print("  exit  → Quit")
    print("  open  → Toggle auto-open frames ON/OFF")
    print()

    while True:
        question = input("Ask: ")

        if question.lower() == "exit":
            break

        if question.lower() == "open":
            AUTO_OPEN_FRAMES = not AUTO_OPEN_FRAMES
            status = "ON" if AUTO_OPEN_FRAMES else "OFF"
            print(f"\n🖼 Auto-open frames is now {status}\n")
            continue

        start_time = time.time()
        result = qs.query(question, top_k=3)
        latency = time.time() - start_time

        answer = result.get("answer", "")
        citations = result.get("citations", [])
        confidence = result.get("confidence", 0)

        print("\n" + "=" * 60)
        print("📌 ANSWER:\n")
        print(answer)
        print("=" * 60)

        print(f"\n🧠 Confidence Score: {confidence}%")
        print(f"\n⏱ Response Time: {latency:.2f} seconds")

        print("\n🔎 SOURCES:\n")

        unique_files = set()

        for c in citations:
            file_name = c.get("source_file")
            if file_name not in unique_files:
                print(f"• {file_name}")
                unique_files.add(file_name)


        print("=" * 60 + "\n")
