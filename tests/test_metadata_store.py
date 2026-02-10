from core.ingestion.pdf_ingest import ingest_pdf
from core.storage.metadata_store import MetadataStore

PDF_PATH = "workspaces/default/uploads/sample.pdf"
DB_PATH = "workspaces/default/storage/metadata/chunks.db"


def main():
    print("=== METADATA STORE TEST STARTED ===")

    # 1. Ingest PDF
    chunks = ingest_pdf(PDF_PATH)
    print(f"Ingested {len(chunks)} chunks")

    # 2. Save metadata
    store = MetadataStore(DB_PATH)
    store.save_chunks(chunks)

    print("Metadata saved to SQLite")

    # 3. Read back one chunk
    sample_chunk = chunks[0]
    loaded = store.get_chunk(sample_chunk.chunk_id)

    assert loaded is not None
    assert loaded.chunk_id == sample_chunk.chunk_id
    assert loaded.source_file == sample_chunk.source_file

    print("Sample chunk loaded successfully:")
    print("Chunk ID:", loaded.chunk_id)
    print("Source:", loaded.source_file)
    print("Page:", loaded.page_number)

    print("=== METADATA STORE TEST FINISHED ===")


if __name__ == "__main__":
    main()
