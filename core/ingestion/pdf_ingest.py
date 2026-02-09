import pdfplumber
from typing import List
from core.schema.chunk import Chunk


def ingest_pdf(file_path: str, chunk_size: int = 200, overlap: int = 40) -> List[Chunk]:
    """
    Convert a PDF file into a list of Chunk objects.
    Each chunk carries page-level citation metadata.
    """
    chunks: List[Chunk] = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            words = text.strip().split()

            start = 0
        

            while start < len(words):
                end = start + chunk_size
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                 
                if len(chunk_text.split()) < 50:
                   start = end - overlap
                   continue
                chunk = Chunk.create(
                    text=chunk_text,
                    source_type="pdf",
                    source_file=file_path.split("/")[-1],
                    page_number=page_number
                )

                chunks.append(chunk)


                start = end - overlap  # overlap

    return chunks
