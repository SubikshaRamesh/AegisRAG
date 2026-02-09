from core.ingestion.pdf_ingest import ingest_pdf

pdf_path = "workspaces/default/uploads/sample.pdf"

chunks = ingest_pdf(pdf_path)

print(f"\nTotal chunks created: {len(chunks)}\n")

for i, chunk in enumerate(chunks[:5]):
    print(f"--- CHUNK {i+1} ---")
    print("Source file :", chunk.source_file)
    print("Page number :", chunk.page_number)
    print("Word count  :", len(chunk.text.split()))
    print("Text preview:")
    print(chunk.text[:400])
    print()
