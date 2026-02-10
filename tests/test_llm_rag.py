import numpy as np

from core.ingestion.pdf_ingest import ingest_pdf
from core.embeddings.embedder import EmbeddingGenerator
from core.vector_store.faiss_manager import FaissManager
from core.retrieval.retriever import Retriever
from core.llm.generator import OfflineLLM


MODEL_PATH = "models/mistral.gguf"
PDF_PATH = "workspaces/default/uploads/sample.pdf"


def main():
    print("=== OFFLINE RAG TEST STARTED ===")

    # 1. Ingest PDF
    chunks = ingest_pdf(PDF_PATH)
    print(f"Ingested {len(chunks)} chunks")

    # 2. Embed chunks
    embedder = EmbeddingGenerator()
    texts = [c.text for c in chunks]
    embeddings = embedder.embed(texts)
    embeddings = np.array(embeddings).astype("float32")

    # 3. Build FAISS index
    faiss_manager = FaissManager(embedding_dim=embeddings.shape[1])
    faiss_manager.add(embeddings, chunks)

    # 4. Retriever
    retriever = Retriever(faiss_manager, chunks)

    # 5. Query
    question = "Where are the Apollo landing sites?"
    query_embedding = embedder.embed([question])
    query_embedding = np.array(query_embedding).astype("float32")

    contexts = retriever.retrieve(query_embedding, top_k=3)

    print("\nRetrieved contexts:")
    for c in contexts:
        print(f"- {c['source_file']} | Page {c['page_number']}")

    # 6. Offline LLM
    llm = OfflineLLM(MODEL_PATH)
    answer = llm.generate_answer(question, contexts)

    print("\n=== FINAL ANSWER ===\n")
    print(answer)
    print("\n=== OFFLINE RAG TEST FINISHED ===")


if __name__ == "__main__":
    main()
