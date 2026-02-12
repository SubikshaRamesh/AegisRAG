from core.ingestion.ingestion_manager import ingest

def test_audio_ingestion():
    audio_path = r"workspaces\default\uploads\sample.mp3"
    source_id = "sample_audio"

    chunks = ingest(
        file_path=audio_path,
        file_type="audio",
        source_id=source_id
    )

    print(f"Number of chunks: {len(chunks)}")
    print("First chunk preview:")
    print(chunks[0].text[:300])
    print("Timestamps:")
    print("Timestamp:", chunks[0].timestamp)



if __name__ == "__main__":
    test_audio_ingestion()
