import os
import subprocess
from typing import List

from core.schema.chunk import Chunk
from core.ingestion.audio_ingest import ingest_audio
from core.embeddings.image_captioner import ImageCaptioner


# -----------------------------------------------------
# AUDIO EXTRACTION
# -----------------------------------------------------

def extract_audio_from_video(
    video_path: str,
    output_dir: str = "temp_video_audio"
) -> str:

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(output_dir, base_name + ".wav")

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
        "-y"
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr.decode()}")

    return audio_path


# -----------------------------------------------------
# VIDEO TRANSCRIPT INGESTION
# -----------------------------------------------------

def ingest_video(video_path: str) -> List[Chunk]:

    audio_path = extract_audio_from_video(video_path)
    audio_chunks = ingest_audio(audio_path, source_id=video_path)

    for chunk in audio_chunks:
        chunk.source_type = "video"

    return audio_chunks


# -----------------------------------------------------
# FRAME EXTRACTION
# -----------------------------------------------------

def extract_frames_from_video(
    video_path: str,
    interval_seconds: int = 10,
    output_dir: str = "temp_video_frames"
):

    os.makedirs(output_dir, exist_ok=True)

    frame_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps=1/{interval_seconds}",
        frame_pattern,
        "-y"
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(f"Frame extraction failed:\n{result.stderr.decode()}")

    return output_dir


# -----------------------------------------------------
# FRAME INGESTION WITH CAPTIONING
# -----------------------------------------------------

_frame_captioner = None

def get_frame_captioner():
    global _frame_captioner
    if _frame_captioner is None:
        _frame_captioner = ImageCaptioner()
    return _frame_captioner


def ingest_video_frames(
    video_path: str,
    interval_seconds: int = 10
) -> List[Chunk]:

    frame_folder = extract_frames_from_video(
        video_path,
        interval_seconds=interval_seconds
    )

    frame_files = sorted([
        os.path.join(frame_folder, f)
        for f in os.listdir(frame_folder)
        if f.endswith(".jpg")
    ])

    if not frame_files:
        return []

    frame_chunks = []
    source_file = os.path.basename(video_path)
    captioner = get_frame_captioner()

    for idx, frame_path in enumerate(frame_files):
        timestamp = idx * interval_seconds
        caption = captioner.generate_caption(frame_path)

        chunk_id = f"{source_file}_frame{idx}"

        chunk = Chunk(
            chunk_id=chunk_id,
            text=caption.strip() if caption else "video frame",
            source_type="video_frame",
            source_file=source_file,
            page_number=frame_path,
            timestamp=timestamp,
        )

        frame_chunks.append(chunk)

    return frame_chunks


# -----------------------------------------------------
# FULL VIDEO INGESTION
# -----------------------------------------------------

def ingest_video_full(video_path: str) -> List[Chunk]:

    audio_chunks = ingest_video(video_path)
    frame_chunks = ingest_video_frames(video_path, interval_seconds=5)

    return audio_chunks + frame_chunks
