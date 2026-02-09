from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import uuid


@dataclass
class Chunk:
    """
    Chunk is the smallest retrievable unit in AegisRAG.
    Each chunk carries its own citation metadata.
    """

    # unique identifier (used to link FAISS ↔ metadata)
    chunk_id: str

    # actual content
    text: str

    # source information
    source_type: str          # pdf | image | audio | video
    source_file: str          # file name only

    # citation fields (optional based on modality)
    page_number: Optional[int] = None      # PDFs
    timestamp: Optional[float] = None      # audio/video (seconds)

    def to_metadata(self) -> Dict[str, Any]:
        """
        Convert Chunk into a serializable metadata dictionary.
        Used for storing metadata in JSON / SQLite.
        """
        return asdict(self)

    @staticmethod
    def create(
        text: str,
        source_type: str,
        source_file: str,
        page_number: Optional[int] = None,
        timestamp: Optional[float] = None,
    ) -> "Chunk":
        """
        Factory method to create a Chunk with a unique ID.
        This should be the ONLY way chunks are created.
        """
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            text=text.strip(),
            source_type=source_type,
            source_file=source_file,
            page_number=page_number,
            timestamp=timestamp,
        )
