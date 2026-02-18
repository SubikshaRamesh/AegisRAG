"""
FastAPI server for AegisRAG production backend.
Exposes REST API endpoints for query and ingestion.
"""

import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from threading import RLock

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from core.logger import get_logger
from core.errors import (
    AegisRAGError,
    IngestionError,
    RetrievalError,
    ValidationError,
)
from core.schemas import QueryRequest
from core.pipeline.query_system import QuerySystem
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.ingestion.ingestion_manager import ingest
from core.storage.metadata_store import MetadataStore
from core.storage.chat_history_store import ChatHistoryStore
from core.utils.translator import Translator

logger = get_logger(__name__)


# ============ GLOBAL STATE ============

query_system: QuerySystem = None
chat_history: ChatHistoryStore = None
translator: Translator = None
chat_sessions: Dict[str, List[Dict[str, str]]] = {}
chat_sessions_lock = RLock()


# ============ REQUEST CORRELATION TRACKING ============

async def add_correlation_id(request: Request, call_next):
    """Add unique correlation ID to each request for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    request.state.start_time = time.time()
    response = await call_next(request)
    return response


# ============ LIFESPAN MANAGEMENT ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.
    """
    # Startup
    logger.info("AegisRAG server starting up...")
    startup()
    logger.info("AegisRAG server ready")

    yield

    # Shutdown
    logger.info("AegisRAG server shutting down...")
    shutdown()
    logger.info("AegisRAG server stopped")


def startup():
    """Initialize query system and chat history on startup."""
    global query_system
    global chat_history
    global translator

    try:
        settings.validate()
        logger.info("Configuration validated")

        # Load existing FAISS indexes
        logger.info("Loading FAISS indexes...")
        text_faiss = FaissManager(
            embedding_dim=settings.TEXT_EMBEDDING_DIM,
            index_path=settings.TEXT_FAISS_INDEX_PATH,
            meta_path=settings.TEXT_FAISS_CHUNK_IDS_PATH,
        )
        logger.info(f"Text FAISS loaded ({len(text_faiss.chunk_ids)} vectors)")

        image_faiss = ImageFaissManager(
            embedding_dim=settings.IMAGE_EMBEDDING_DIM,
            index_path=settings.IMAGE_FAISS_INDEX_PATH,
            meta_path=settings.IMAGE_FAISS_CHUNK_IDS_PATH,
        )
        logger.info(f"Image FAISS loaded ({len(image_faiss.chunk_ids)} vectors)")

        # Initialize translator for Tamil-to-English translations
        logger.info("Loading Tamil-English translator...")
        translator = Translator()
        logger.info("Tamil-English translator loaded successfully")

        # Initialize query system (ONCE at startup)
        logger.info("Initializing multilingual embedding models...")
        query_system = QuerySystem(
            text_faiss=text_faiss,
            image_faiss=image_faiss,
            db_path=settings.DB_PATH,
            model_path=settings.LLM_MODEL_PATH,
            translator=translator,
        )
        logger.info("Multilingual embedding model loaded successfully")
        logger.info("Query system initialized (models loaded)")

        # Initialize chat history store
        logger.info("Initializing chat history store...")
        chat_history = ChatHistoryStore(db_path=settings.DB_PATH)
        logger.info("Chat history store initialized")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


def shutdown():
    """Clean up resources on shutdown."""
    global query_system

    if query_system:
        logger.info("Saving FAISS indexes...")
        query_system.text_faiss.save()
        query_system.image_faiss.save()
        logger.info("Indexes saved")


# ============ FASTAPI APP ============

app = FastAPI(
    title="AegisRAG API",
    description="Fully offline multimodal RAG system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def append_session_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the in-memory session history with max length 10."""
    with chat_sessions_lock:
        history = chat_sessions.setdefault(session_id, [])
        history.append({"role": role, "content": content, "timestamp": time.time()})
        if len(history) > 10:
            chat_sessions[session_id] = history[-10:]


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """Get full session history for a session id."""
    with chat_sessions_lock:
        return list(chat_sessions.get(session_id, []))

# Request correlation middleware
app.middleware("http")(add_correlation_id)


# ============ HEALTH & STATUS ============

@app.get("/health")
async def health_check() -> Dict:
    """
    Health check endpoint.
    Returns 200 if system is ready.
    """
    try:
        if query_system is None:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "message": "System initializing..."},
            )

        return {
            "status": "healthy",
            "text_vectors": len(query_system.text_faiss.chunk_ids),
            "image_vectors": len(query_system.image_faiss.chunk_ids),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)},
        )


@app.get("/status")
async def status() -> Dict:
    """
    System status endpoint.
    Returns detailed system information.
    """
    try:
        if query_system is None:
            raise RuntimeError("Query system not initialized")

        return {
            "status": "running",
            "text_embedder": "MiniLM-L6-v2",
            "clip_embedder": "OpenAI CLIP",
            "llm_model": settings.LLM_MODEL_PATH,
            "text_vectors": len(query_system.text_faiss.chunk_ids),
            "image_vectors": len(query_system.image_faiss.chunk_ids),
            "vector_dim": {
                "text": settings.TEXT_EMBEDDING_DIM,
                "image": settings.IMAGE_EMBEDDING_DIM,
            },
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ QUERY ENDPOINT ============

@app.post("/query")
async def query_endpoint(
    query_request: QueryRequest,
    request: Request = None,
) -> Dict:
    """
    Main RAG query endpoint.

    Args:
        query_request: QueryRequest model with question and top_k

    Returns:
        Dict with answer, sources, and confidence score
    """
    correlation_id = request.state.correlation_id if request else str(uuid.uuid4())
    start_time = time.time()

    try:
        if query_system is None:
            raise RuntimeError("Query system not initialized")

        question = query_request.question
        session_id = query_request.session_id
        top_k = settings.RETRIEVAL_TOP_K

        logger.info(f"[{correlation_id}] Question: {question[:100]}...")

        append_session_message(session_id, "user", question)
        history_for_prompt = get_session_history(session_id)[-3:]

        # Execute query
        result = query_system.query(
            question,
            top_k=top_k,
            history_messages=history_for_prompt,
        )
        elapsed_time = time.time() - start_time

        answer = result.get("answer", "")
        append_session_message(session_id, "assistant", answer)

        # Save to chat history
        try:
            chat_history.save_interaction(
                question=question,
                answer=result.get("answer", ""),
                sources=result.get("sources", [])
            )
        except Exception as e:
            logger.warning(f"[{correlation_id}] Failed to save chat history: {e}")

        logger.info(
            f"[{correlation_id}] Query complete - "
            f"confidence: {result['confidence']}%, "
            f"sources: {len(result.get('sources', []))}, "
            f"elapsed: {elapsed_time:.2f}s"
        )

        sources = []
        for source in result.get("sources", []):
            sources.append({
                "type": source.get("source_type", "unknown"),
                "source": source.get("source_file", ""),
                "score": source.get("score", 0),
            })

        return {
            "answer": answer,
            "confidence": result.get("confidence", 0),
            "sources": sources,
        }

    except ValidationError as e:
        logger.warning(f"[{correlation_id}] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RetrievalError as e:
        logger.error(f"[{correlation_id}] Retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")
    except Exception as e:
        logger.error(f"[{correlation_id}] Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============ INGESTION ENDPOINT ============

def cleanup_temp_files():
    """Remove temporary files after ingestion."""
    for temp_dir in [settings.TEMP_VIDEO_AUDIO_DIR, settings.TEMP_VIDEO_FRAMES_DIR]:
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Cleaned up {temp_dir}")


async def handle_ingest(
    file: UploadFile,
    file_type: str,
    background_tasks: BackgroundTasks,
    request: Request,
) -> Dict:
    """
    File ingestion endpoint.
    Uploads and processes a file (PDF, DOCX, Image, Audio, Video).

    Args:
        file: The file to ingest
        file_type: Type of file (pdf, docx, image, audio, video)
                   If None, auto-detect from extension

    Returns:
        Dict with ingestion status and chunk count
    """
    correlation_id = request.state.correlation_id if request else str(uuid.uuid4())
    start_time = time.time()

    try:
        if query_system is None:
            raise RuntimeError("Query system not initialized")

        # Validate file
        if not file.filename:
            raise ValidationError("Filename required")

        # Read file once and calculate size properly
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)

        if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValidationError(
                f"File too large: {file_size_mb:.1f}MB "
                f"(max: {settings.MAX_UPLOAD_SIZE_MB}MB)"
            )

        # Determine file type
        if not file_type:
            ext = Path(file.filename).suffix.lower().lstrip(".")
            if ext == "docx":
                file_type = "docx"
            elif ext in ["jpg", "jpeg", "png", "gif", "bmp"]:
                file_type = "image"
            elif ext in ["mp3", "wav", "m4a", "flac"]:
                file_type = "audio"
            elif ext in ["mp4", "avi", "mov", "mkv"]:
                file_type = "video"
            elif ext == "pdf":
                file_type = "pdf"
            else:
                raise ValidationError(f"Unsupported file type: .{ext}")

        if file_type not in settings.SUPPORTED_FILE_TYPES:
            raise ValidationError(
                f"Unsupported file type: {file_type}. "
                f"Supported: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
            )

        # Save uploaded file (contents already read)
        upload_dir = settings.UPLOADS_PATH
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename

        with open(file_path, "wb") as f:
            f.write(contents)

        logger.info(
            f"[{correlation_id}] Ingesting {file.filename} ({file_type}) "
            f"({file_size_mb:.1f}MB)..."
        )

        # Process file
        chunks = ingest(str(file_path), file_type, source_id=file.filename)

        if not chunks:
            logger.warning(f"[{correlation_id}] No chunks extracted from {file.filename}")
            return {
                "status": "warning",
                "filename": file.filename,
                "file_type": file_type,
                "chunks_created": 0,
                "message": f"No chunks extracted from {file.filename}",
            }

        # Use embedders from query_system (initialized once at startup)
        import numpy as np

        chunks_added = 0
        if file_type == "image":
            # Image chunks go to image FAISS (use CLIP from query_system)
            embeddings = query_system.clip_embedder.embed_text(
                [c.text for c in chunks]
            )
            embeddings = np.array(embeddings).astype("float32")
            chunks_added = query_system.image_faiss.add(embeddings, chunks)
            # Only save if vectors were actually added
            if chunks_added > 0:
                query_system.image_faiss.save()
        else:
            # Text/audio/video chunks go to text FAISS (use MiniLM from query_system)
            embeddings = query_system.text_embedder.embed([c.text for c in chunks])
            embeddings = np.array(embeddings).astype("float32")
            chunks_added = query_system.text_faiss.add(embeddings, chunks)
            # Only save if vectors were actually added
            if chunks_added > 0:
                query_system.text_faiss.save()

        elapsed_time = time.time() - start_time

        logger.info(
            f"[{correlation_id}] Ingestion complete: "
            f"{chunks_added} chunks added, {len(chunks) - chunks_added} duplicates skipped, "
            f"elapsed {elapsed_time:.2f}s"
        )

        # Schedule cleanup
        if background_tasks:
            background_tasks.add_task(cleanup_temp_files)

        return {
            "status": "success",
            "filename": file.filename,
            "file_type": file_type,
            "chunks_extracted": len(chunks),
            "chunks_added": chunks_added,
            "duplicates_skipped": len(chunks) - chunks_added,
            "processing_time_seconds": round(elapsed_time, 2),
            "message": f"Successfully ingested {chunks_added} new chunks from {file.filename}",
        }

    except ValidationError as e:
        logger.warning(f"[{correlation_id}] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except IngestionError as e:
        logger.error(f"[{correlation_id}] Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    except Exception as e:
        logger.error(f"[{correlation_id}] Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_endpoint(
    file: UploadFile = File(...),
    file_type: str = None,
    background_tasks: BackgroundTasks = None,
    request: Request = None,
) -> Dict:
    """Backward-compatible ingestion endpoint."""
    return await handle_ingest(file, file_type, background_tasks, request)


@app.post("/upload")
async def upload_endpoint(
    file: UploadFile = File(...),
    file_type: str = None,
    background_tasks: BackgroundTasks = None,
    request: Request = None,
) -> Dict:
    """File upload endpoint for the frontend."""
    return await handle_ingest(file, file_type, background_tasks, request)


# ============ ERROR HANDLERS ============

@app.exception_handler(AegisRAGError)
async def aegisrag_exception_handler(request, exc):
    logger.error(f"AegisRAG error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ============ ROOT ENDPOINT ============

@app.get("/")
async def root() -> Dict:
    """Root endpoint with API information."""
    return {
        "name": "AegisRAG API",
        "version": "1.0.0",
        "description": "Fully offline multimodal RAG system",
        "endpoints": {
            "GET /health": "Health check",
            "GET /status": "System status",
            "POST /query": "Query the knowledge base",
            "POST /upload": "Upload and ingest a file",
            "POST /ingest": "Ingest a file (legacy)",
            "GET /history/{session_id}": "Get in-memory session history",
            "GET /history": "Get persisted chat history",
            "GET /history/search": "Search chat history",
            "DELETE /history": "Clear chat history",
            "GET /files": "Get file inventory",
            "GET /files/search": "Search files",
        },
    }


# ============ CHAT HISTORY ENDPOINTS ============

@app.get("/history")
async def get_history(limit: int = 100, offset: int = 0) -> Dict:
    """
    Get chat history ordered by newest first.

    Query Parameters:
        limit: Maximum number of records (default: 100)
        offset: Number of records to skip (default: 0)

    Returns:
        List of chat history records with question, answer, sources, timestamp
    """
    try:
        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        history = chat_history.get_history(limit=limit, offset=offset)

        return {
            "status": "success",
            "count": len(history),
            "limit": limit,
            "offset": offset,
            "history": history
        }

    except Exception as e:
        logger.error(f"Failed to retrieve chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{session_id}")
async def get_session_history_endpoint(session_id: str) -> Dict:
    """Get in-memory session history for a specific session."""
    if not session_id or not session_id.strip():
        raise HTTPException(status_code=400, detail="Session ID is required")

    history = get_session_history(session_id)

    return {
        "status": "success",
        "session_id": session_id,
        "count": len(history),
        "history": history,
    }


@app.get("/history/search")
async def search_history(query: str) -> Dict:
    """
    Search chat history by question or answer.

    Query Parameters:
        query: Search term (case-insensitive)

    Returns:
        List of matching chat history records
    """
    try:
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        results = chat_history.search_history(query=query.strip())

        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to search chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history")
async def clear_history() -> Dict:
    """
    Delete all chat history.

    Returns:
        Number of records deleted
    """
    try:
        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        deleted_count = chat_history.clear_history()

        return {
            "status": "success",
            "message": f"Deleted {deleted_count} chat history records",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============ FILE INVENTORY ENDPOINTS ============

@app.get("/files")
async def get_files_inventory() -> Dict:
    """
    Get inventory of all ingested files.

    Returns:
        List of files with:
            - file_name: Source file name
            - total_chunks: Number of chunks from this file
            - first_ingested_timestamp: Earliest chunk timestamp
            - last_ingested_timestamp: Latest chunk timestamp
    """
    try:
        if query_system is None:
            raise RuntimeError("Query system not initialized")

        metadata_store = MetadataStore(db_path=settings.DB_PATH)
        files = metadata_store.get_files_inventory()

        return {
            "status": "success",
            "count": len(files),
            "files": files
        }

    except Exception as e:
        logger.error(f"Failed to retrieve file inventory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/search")
async def search_files(query: str) -> Dict:
    """
    Search for ingested files by name.

    Query Parameters:
        query: File name search term (case-insensitive)

    Returns:
        List of matching files with metadata
    """
    try:
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        metadata_store = MetadataStore(db_path=settings.DB_PATH)
        results = metadata_store.search_files(query=query.strip())

        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to search files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============ MAIN ============

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
