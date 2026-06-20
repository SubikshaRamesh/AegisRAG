from sentence_transformers import SentenceTransformer
from core.logger import get_logger

logger = get_logger(__name__)

_shared_embedder = None

class EmbeddingGenerator:
    """
    Loads embedding model ONCE.
    """

    def __init__(self):
        logger.info("Loading embedding model once at startup...")
        self.model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cpu"
)
        logger.info("Embedding model loaded.")

    def embed(self, texts):
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )


def get_embedding_generator() -> EmbeddingGenerator:
    global _shared_embedder
    if _shared_embedder is None:
        _shared_embedder = EmbeddingGenerator()
    return _shared_embedder
