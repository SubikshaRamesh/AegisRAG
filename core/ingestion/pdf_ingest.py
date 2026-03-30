import pdfplumber
from typing import List
from core.schema.chunk import Chunk
import os
import re


def clean_text(text: str) -> str:
    """
    Normalize PDF extracted text for cleaner RAG ingestion.
    """

    # Replace newlines with space
    text = text.replace("\n", " ")

    # Fix repeated commas (",,")
    text = re.sub(r",\s*,+", ", ", text)

    # Fix repeated colons ("::")
    text = re.sub(r":\s*:+", ":", text)

    # Fix broken parentheses "( :"
    text = re.sub(r"\(\s*:", "(", text)

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Remove strange spacing before punctuation
    text = re.sub(r"\s+([.,;:])", r"\1", text)

    return text.strip()


def ingest_pdf(file_path: str, chunk_size: int = 200, overlap: int = 40) -> List[Chunk]:
    """
    Convert a PDF file into deterministic Chunk objects.
    Cleaned + normalized for high-quality RAG.
    """
    chunks: List[Chunk] = []

    source_file = os.path.basename(file_path)

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text()
            if not raw_text:
                continue

            # 🔥 Clean text BEFORE chunking
            text = clean_text(raw_text)

            words = text.split()
            start = 0
            chunk_index = 0

            while start < len(words):
                end = start + chunk_size
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)

                if len(chunk_words) < 50:
                    start = end - overlap
                    continue

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