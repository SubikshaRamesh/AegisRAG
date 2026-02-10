import numpy as np
from core.ingestion.pdf_ingest import ingest_pdf
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.retrieval.retriever import Retriever

pdf_path = "workspaces/default/uploads/sample.pdf"

# 1. Ingest
chunks = ingest_pdf(pdf_path)

# 2. Embed chunks
embedder = EmbeddingGenerator()
texts = [c.text for c in chunks]
embeddings = embedder.embed(texts)
embeddings = np.array(embeddings).astype("float32")

# 3. FAISS index
faiss_manager = FaissManager(embedding_dim=embeddings.shape[1])
faiss_manager.add(embeddings, chunks)

# 4. Retriever
retriever = Retriever(faiss_manager, chunks)

# 5. Query
query = "Where did the Apollo missions land?"
query_embedding = embedder.embed([query])
query_embedding = np.array(query_embedding).astype("float32")

results = retriever.retrieve(query_embedding, top_k=3)

print("\nRETRIEVER RESULTS:\n")
for r in results:
    print("Source:", r["source_file"], "| Page:", r["page_number"])
    print("Distance:", r["distance"])
    print(r["text"][:300])
    print("-" * 50)
