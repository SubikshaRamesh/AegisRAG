print("TEST EMBEDDING SCRIPT STARTED")

from core.ingestion.pdf_ingest import ingest_pdf
from core.embeddings.embedder import EmbeddingGenerator

pdf_path = "workspaces/default/uploads/sample.pdf"

chunks = ingest_pdf(pdf_path)
print("Chunks loaded:", len(chunks))

texts = [chunk.text for chunk in chunks]

embedder = EmbeddingGenerator()
embeddings = embedder.embed(texts)

print("Embedding dimension:", len(embeddings[0]))
print("TEST EMBEDDING SCRIPT FINISHED")
