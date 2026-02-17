"""
Production configuration system for AegisRAG.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Global production settings."""

    # ============ SERVER ============
    HOST: str = os.getenv("AEGIS_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("AEGIS_PORT", "8000"))
    DEBUG: bool = os.getenv("AEGIS_DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("AEGIS_LOG_LEVEL", "INFO")

    # ============ STORAGE & PATHS ============
    WORKSPACE_ROOT: Path = Path(os.getenv("AEGIS_WORKSPACE", "./workspaces/default"))
    STORAGE_PATH: Path = WORKSPACE_ROOT / "storage"
    UPLOADS_PATH: Path = WORKSPACE_ROOT / "uploads"
    METADATA_PATH: Path = STORAGE_PATH / "metadata"
    DATA_PATH: Path = Path(os.getenv("AEGIS_DATA_PATH", "./data"))
    MODELS_PATH: Path = Path(os.getenv("AEGIS_MODELS_PATH", "./models"))

    # Create directories if they don't exist
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.mkdir(parents=True, exist_ok=True)

    # ============ DATABASE ============
    DB_PATH: str = str(METADATA_PATH / "chunks.db")

    # ============ VECTOR STORES ============
    TEXT_FAISS_INDEX_PATH: str = str(METADATA_PATH / "faiss.index")
    TEXT_FAISS_CHUNK_IDS_PATH: str = str(METADATA_PATH / "chunk_ids.pkl")
    TEXT_EMBEDDING_DIM: int = 384

    IMAGE_FAISS_INDEX_PATH: str = str(METADATA_PATH / "image_faiss.index")
    IMAGE_FAISS_CHUNK_IDS_PATH: str = str(METADATA_PATH / "image_chunk_ids.pkl")
    IMAGE_EMBEDDING_DIM: int = 512

    # ============ MODELS ============
    TEXT_EMBEDDER_MODEL: str = os.getenv(
        "TEXT_EMBEDDER_MODEL", 
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    CLIP_MODEL: str = os.getenv("CLIP_MODEL", "ViT-B-16")
    CLIP_PRETRAINED: str = os.getenv("CLIP_PRETRAINED", "openai")
    
    LLM_MODEL_PATH: str = str(MODELS_PATH / "Phi-3-mini-4k-instruct-q4.gguf")
    LLM_CONTEXT_SIZE: int = int(os.getenv("LLM_CONTEXT_SIZE", "2048"))
    LLM_THREADS: int = int(os.getenv("LLM_THREADS", "12"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "120"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    # ============ RETRIEVAL ============
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "3"))
    FAISS_DISTANCE_THRESHOLD: float = float(os.getenv("FAISS_DISTANCE_THRESHOLD", "1.0"))

    # ============ INGESTION ============
    SUPPORTED_FILE_TYPES: list = ["pdf", "docx", "image", "audio", "video"]
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
    TEMP_VIDEO_AUDIO_DIR: Path = Path("./temp_video_audio")
    TEMP_VIDEO_FRAMES_DIR: Path = Path("./temp_video_frames")

    # ============ API ============
    API_TIMEOUT_SECONDS: int = int(os.getenv("API_TIMEOUT_SECONDS", "120"))
    QUERY_TIMEOUT_SECONDS: int = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))
    INGEST_TIMEOUT_SECONDS: int = int(os.getenv("INGEST_TIMEOUT_SECONDS", "300"))

    # ============ LOGGING ============
    LOG_FILE_PATH: Optional[Path] = (
        Path(os.getenv("LOG_FILE_PATH", "./logs/aegisrag.log"))
        if os.getenv("LOG_FILE_PATH") or os.getenv("AEGIS_LOG_LEVEL") == "DEBUG"
        else None
    )

    @classmethod
    def validate(cls):
        """Validate essential settings at startup."""
        if not cls.MODELS_PATH.exists():
            raise RuntimeError(f"Models directory not found: {cls.MODELS_PATH}")
        
        # Check if LLM model exists
        if not Path(cls.LLM_MODEL_PATH).exists():
            raise RuntimeError(f"LLM model not found: {cls.LLM_MODEL_PATH}")
        
        return True


# Singleton instance
settings = Settings()
