import os
from typing import List
import whisper

from core.schema.chunk import Chunk


# Load Whisper model once (offline)
_model = whisper.load_model("small")


def transcribe_audio(audio_path: str):
    """
    Convert audio file into timestamped text segments using Whisper.
    """
    result = _model.transcribe(audio_path)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "text": seg["text"].strip(),
            "start_time": seg["start"],
            "end_time": seg["end"]
        })

    return segments


def merge_audio_segments(
    segments,
    min_words: int = 120,
    max_words: int = 200
):
    """
    Merge small Whisper segments into larger semantic chunks.
    Preserves timestamps.
    """

    merged = []

    buffer_text = []
    buffer_word_count = 0
    start_time = None

    for seg in segments:
        if not seg["text"].strip():
            continue

        words = seg["text"].split()
        word_count = len(words)

        if start_time is None:
            start_time = seg["start_time"]

        buffer_text.append(seg["text"])
        buffer_word_count += word_count
        end_time = seg["end_time"]

        # Flush condition
        if buffer_word_count >= min_words or buffer_word_count >= max_words:
            merged.append({
                "text": " ".join(buffer_text),
                "start_time": start_time,
                "end_time": end_time
            })

            buffer_text = []
            buffer_word_count = 0
            start_time = None

    # Flush remaining buffer
    if buffer_text:
        merged.append({
            "text": " ".join(buffer_text),
            "start_time": start_time,
            "end_time": end_time
        })

    return merged


def ingest_audio(file_path: str, source_id: str) -> List[Chunk]:
    """
    Full audio ingestion pipeline:
    1. Transcribe audio
    2. Merge segments
    3. Convert into Chunk objects
    """

    # 1️⃣ Transcribe audio
    segments = transcribe_audio(file_path)

    # 2️⃣ Merge into larger chunks
    merged_segments = merge_audio_segments(segments)

    chunks: List[Chunk] = []

    # 3️⃣ Convert to Chunk objects
    for seg in merged_segments:
        chunk = Chunk.create(
            text=seg["text"],
            source_type="audio",
            source_file=os.path.basename(source_id),
            timestamp=seg["start_time"],
        )
        chunks.append(chunk)

    return chunks
