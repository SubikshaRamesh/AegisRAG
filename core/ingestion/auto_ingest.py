import os

from core.ingestion.ingestion_manager import ingest


UPLOAD_DIR = "workspaces/default/uploads"


def auto_ingest_workspace() -> None:
    """
    Automatically scans uploads folder and ingests all supported files.
    Uses ingestion_manager so FAISS is updated.
    """

    if not os.path.exists(UPLOAD_DIR):
        raise FileNotFoundError(f"Uploads folder not found: {UPLOAD_DIR}")

    print("\n🚀 Starting automatic ingestion...\n")

    file_count = 0

    for file_name in os.listdir(UPLOAD_DIR):

        file_path = os.path.join(UPLOAD_DIR, file_name)

        if not os.path.isfile(file_path):
            continue

        extension = file_name.lower().split(".")[-1]

        # Map extension → logical type
        if extension == "pdf":
            file_type = "pdf"
        elif extension == "docx":
            file_type = "docx"
        elif extension in ["mp3", "wav"]:
            file_type = "audio"
        elif extension in ["mp4", "mov", "avi"]:
            file_type = "video"
        elif extension in ["jpg", "jpeg", "png"]:
            file_type = "image"
        else:
            print(f"⚠ Skipping unsupported file type: {file_name}")
            continue

        try:
            print(f"🔹 Processing: {file_name}")

            ingest(file_path, file_type, source_id=file_name)

            file_count += 1
            print(f"   ✅ Ingested successfully.\n")

        except Exception as e:
            print(f"❌ Failed processing {file_name}: {e}\n")

    print("==========================================")
    print(f"📁 Files Processed: {file_count}")
    print("==========================================\n")

    print("✅ Automatic ingestion complete.\n")
