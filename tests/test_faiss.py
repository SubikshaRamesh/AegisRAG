import numpy as np
from core.ingestion.pdf_ingest import ingest_pdf
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager

pdf_path = "workspaces/default/uploads/sample.pdf"

# 1. Ingest PDF
chunks = ingest_pdf(pdf_path)
texts = [c.text for c in chunks]

# 2. Embed chunks
embedder = EmbeddingGenerator()
embeddings = embedder.embed(texts)
embeddings = np.array(embeddings).astype("float32")

# 3. Build FAISS index
faiss_manager = FaissManager(embedding_dim=embeddings.shape[1])
faiss_manager.add(embeddings, chunks)

# 4. Query FAISS
query = "Where are the Apollo landing sites?"
query_embedding = embedder.embed([query])
query_embedding = np.array(query_embedding).astype("float32")

results = faiss_manager.search(query_embedding, top_k=3)

print("\nFAISS RESULTS:")
for r in results:
    print(r)
