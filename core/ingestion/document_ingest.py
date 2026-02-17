import os
from typing import List
from docx import Document

from core.schema.chunk import Chunk


def ingest_docx(file_path: str) -> List[Chunk]:
    """
    Structured DOCX ingestion with deterministic chunk IDs.
    Groups content under headings.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"DOCX file not found: {file_path}")

    doc = Document(file_path)

    structured_data = []
    current_heading = "General"

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if para.style.name.startswith("Heading"):
            current_heading = text
        else:
            structured_data.append({
                "heading": current_heading,
                "text": text,
            })

    chunks: List[Chunk] = []
    source_file = os.path.basename(file_path)

    current_text = ""
    current_heading = None
    chunk_index = 0

    for item in structured_data:

        if item["heading"] != current_heading:

            if current_text:
                chunk = Chunk.create(
                    text=current_text.strip(),
                    source_type="docx",
                    source_file=source_file,
                    page_number=None,
                    timestamp=None,
                )
                chunks.append(chunk)
                chunk_index += 1

            current_heading = item["heading"]
            current_text = item["text"]

        else:
            current_text += " " + item["text"]

    if current_text:
        chunk = Chunk.create(
            text=current_text.strip(),
            source_type="docx",
            source_file=source_file,
            page_number=None,
            timestamp=None,
        )
        chunks.append(chunk)

    return chunks
