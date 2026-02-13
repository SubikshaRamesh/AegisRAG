import os
from core.ingestion.ingestion_manager import ingest

if __name__ == "__main__":
    upload_dir = r"workspaces/default/uploads"

    for file in os.listdir(upload_dir):

        if not file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff")):
            continue

        image_path = os.path.join(upload_dir, file)

        print(f"\n🔹 Ingesting: {file}")

        chunks = ingest(
            file_path=image_path,
            file_type="image",
            source_id=file
        )

        print("Total chunks created:", len(chunks))

        for c in chunks:
            print("Type:", c.source_type)
            print("Preview:", c.text[:100])
            print("-" * 40)
