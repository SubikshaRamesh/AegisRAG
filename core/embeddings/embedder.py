from sentence_transformers import SentenceTransformer
from core.logger import get_logger

logger = get_logger(__name__)

class EmbeddingGenerator:
    """
    Loads embedding model ONCE.
    """

    def __init__(self):
        logger.info("Loading embedding model once at startup...")
        self.model = SentenceTransformer(
            "models/embedding",
            device="cpu"
        )
        logger.info("Embedding model loaded.")

    def embed(self, texts):
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
