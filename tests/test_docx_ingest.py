from core.ingestion.ingestion_manager import ingest

if __name__ == "__main__":
    file_path = "workspaces/default/uploads/sample.docx"

    chunks = ingest(
        file_path=file_path,
        file_type="docx",
        source_id="sample_docx"
    )

    print("Total DOCX chunks:", len(chunks))
