import os
from typing import List
from PIL import Image
import pytesseract

from core.schema.chunk import Chunk
from core.embeddings.image_captioner import ImageCaptioner


# Set exact Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# --------------------------------------------------
# Singleton Captioner (Loads BLIP only once)
# --------------------------------------------------
_captioner = None

def get_captioner():
    global _captioner
    if _captioner is None:
        _captioner = ImageCaptioner()
    return _captioner


def ingest_image(file_path: str) -> List[Chunk]:
    """
    Deterministic image ingestion:

    1️⃣ OCR text chunk
    2️⃣ Caption chunk
    3️⃣ Visual chunk (for CLIP)
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    chunks: List[Chunk] = []

    source_file = os.path.basename(file_path)

    # --------------------------------------------------
    # 1️⃣ OCR TEXT CHUNK
    # --------------------------------------------------
    try:
        img = Image.open(file_path).convert("L")
        extracted_text = pytesseract.image_to_string(img, lang="eng")

        if extracted_text.strip():
            chunk_id = f"{source_file}_ocr"

            text_chunk = Chunk(
                chunk_id=chunk_id,
                text=extracted_text.strip(),
                source_type="image_text",
                source_file=source_file,
                timestamp=None,
            )
            chunks.append(text_chunk)

    except Exception as e:
        print(f"OCR failed for {file_path}: {e}")

    # --------------------------------------------------
    # 2️⃣ IMAGE CAPTION CHUNK
    # --------------------------------------------------
    try:
        captioner = get_captioner()
        caption = captioner.generate_caption(file_path)

        if caption and caption.strip():
            chunk_id = f"{source_file}_caption"

            caption_chunk = Chunk(
                chunk_id=chunk_id,
                text=caption.strip(),
                source_type="image_caption",
                source_file=source_file,
                timestamp=None,
            )
            chunks.append(caption_chunk)

    except Exception as e:
        print(f"Captioning failed for {file_path}: {e}")

    # --------------------------------------------------
    # 3️⃣ VISUAL CHUNK (CLIP reference)
    # --------------------------------------------------
    visual_chunk_id = f"{source_file}_visual"

    visual_chunk = Chunk(
        chunk_id=visual_chunk_id,
        text=file_path,  # store path for CLIP embedding regeneration
        source_type="image",
        source_file=source_file,
        timestamp=None,
    )

    chunks.append(visual_chunk)

    return chunks
