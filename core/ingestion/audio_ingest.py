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

        if buffer_word_count >= min_words:
            merged.append({
                "text": " ".join(buffer_text),
                "start_time": start_time,
                "end_time": end_time
            })

            buffer_text = []
            buffer_word_count = 0
            start_time = None

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
    3. Convert into deterministic Chunk objects
    """

    segments = transcribe_audio(file_path)
    merged_segments = merge_audio_segments(segments)

    chunks: List[Chunk] = []

    source_file = os.path.basename(file_path)

    for idx, seg in enumerate(merged_segments):

        # Deterministic chunk_id
        chunk_id = f"{source_file}_segment{idx}"

        chunk = Chunk(
            chunk_id=chunk_id,
            text=seg["text"],
            source_type="audio",
            source_file=source_file,
            timestamp=seg["start_time"],  # Only start time stored
        )

        chunks.append(chunk)

    return chunks
