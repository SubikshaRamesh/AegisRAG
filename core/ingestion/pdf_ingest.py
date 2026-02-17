import pdfplumber
from typing import List
from core.schema.chunk import Chunk
import os


def ingest_pdf(file_path: str, chunk_size: int = 200, overlap: int = 40) -> List[Chunk]:
    """
    Convert a PDF file into deterministic Chunk objects.
    Each chunk has stable chunk_id for duplicate prevention.
    """
    chunks: List[Chunk] = []

    source_file = os.path.basename(file_path)

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            words = text.strip().split()
            start = 0
            chunk_index = 0

            while start < len(words):
                end = start + chunk_size
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)

                if len(chunk_words) < 50:
                    start = end - overlap
                    continue

                # 🔥 Deterministic chunk_id
                chunk_id = f"{source_file}_page{page_number}_chunk{chunk_index}"

                chunk = Chunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    source_type="pdf",
                    source_file=source_file,
                    page_number=page_number,
                )

                chunks.append(chunk)

                chunk_index += 1
                start = end - overlap

    return chunks
