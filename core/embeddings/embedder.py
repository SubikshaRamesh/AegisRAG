from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingGenerator:
    def __init__(self):
        # Small, fast, fully offline
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    def embed(self, texts: List[str]):
        return self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True
        )
