from sentence_transformers import SentenceTransformer
from typing import List
from core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """
    Multilingual text embedding using paraphrase-multilingual-MiniLM-L12-v2.
    
    IMPORTANT:
    This model is not compatible with embeddings from all-MiniLM-L6-v2.
    If upgrading from a previous embedding model:
    - Delete existing FAISS indexes (workspaces/default/storage/metadata/faiss.index*)
    - Delete SQLite database (workspaces/default/storage/metadata/chunks.db)
    - Re-ingest all documents
    """
    
    def __init__(self):
        # Multilingual model supporting 50+ languages
        # Produces 384-dim vectors (same as previous model)
        # Loaded once at startup, reused for all embeddings
        logger.info("Loading multilingual embedding model...")
        self.model = SentenceTransformer(
            "models/embedding",
            local_files_only=True
        )
        logger.info("Multilingual embedding model loaded successfully")

    def embed(self, texts: List[str]):
        return self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True
        )
