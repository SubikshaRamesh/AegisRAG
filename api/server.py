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
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from config.settings import settings
from core.logger import get_logger
from core.errors import (
    AegisRAGError,
    IngestionError,
    RetrievalError,
    ValidationError,
)
from core.schemas import QueryRequest, ChatCreateResponse, ChatHistoryResponse, ConversationSummary
from core.pipeline.query_system import QuerySystem
from core.vector_store.faiss_manager import FaissManager
from core.vector_store.image_faiss_manager import ImageFaissManager
from core.ingestion.ingestion_manager import ingest
from core.storage.metadata_store import MetadataStore
from core.storage.chat_history_store import ChatHistoryStore

logger = get_logger(__name__)


# ============ GLOBAL STATE ============

query_system: QuerySystem = None
chat_history: ChatHistoryStore = None
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
    try:
        settings.validate()
        logger.info("Configuration validated")

        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        # ============ LOAD FAISS INDEXES ============
        logger.info("Loading FAISS indexes...")
        load_start = time.time()
        text_faiss = FaissManager(
            embedding_dim=settings.TEXT_EMBEDDING_DIM,
            index_path=settings.TEXT_FAISS_INDEX_PATH,
            meta_path=settings.TEXT_FAISS_CHUNK_IDS_PATH,
        )
        text_load_time = time.time() - load_start
        logger.info(f"✓ Text FAISS loaded ({len(text_faiss.chunk_ids)} vectors) in {text_load_time:.3f}s")

        load_start = time.time()
        image_faiss = ImageFaissManager(
            embedding_dim=settings.IMAGE_EMBEDDING_DIM,
            index_path=settings.IMAGE_FAISS_INDEX_PATH,
            meta_path=settings.IMAGE_FAISS_CHUNK_IDS_PATH,
        )
        image_load_time = time.time() - load_start
        logger.info(f"✓ Image FAISS loaded ({len(image_faiss.chunk_ids)} vectors) in {image_load_time:.3f}s")

        # ============ INITIALIZE QUERY SYSTEM (ONCE at startup) ============
        logger.info("Initializing QuerySystem (embedding models + LLM)...")
        qs_start = time.time()
        query_system = QuerySystem(
            text_faiss=text_faiss,
            image_faiss=image_faiss,
            db_path=settings.DB_PATH,
            model_path=settings.LLM_MODEL_PATH,
        )
        qs_load_time = time.time() - qs_start
        logger.info(f"✓ QuerySystem initialized in {qs_load_time:.3f}s")
        logger.info(f"  - QuerySystem object ID: {id(query_system)} (GLOBAL singleton)")

        # ============ INITIALIZE CHAT HISTORY ============
        logger.info("Initializing ChatHistoryStore...")
        chat_start = time.time()
        chat_history = ChatHistoryStore(db_path=settings.DB_PATH)
        chat_load_time = time.time() - chat_start
        logger.info(f"✓ ChatHistoryStore initialized in {chat_load_time:.3f}s")

        # ============ VALIDATION CHECKS ============
        logger.info("━" * 60)
        logger.info("INITIALIZATION COMPLETE - PERFORMANCE CHECKLIST")
        logger.info("━" * 60)
        logger.info(f"✓ QuerySystem is GLOBAL singleton (ID: {id(query_system)})")
        logger.info(f"✓ query_system.text_embedder: {id(query_system.text_embedder)} (ONCE created)")
        logger.info(f"✓ query_system.llm: {id(query_system.llm)} (ONCE created)")
        logger.info("✓ All models LOCKED in memory (no reload per request)")
        logger.info("✓ FAISS indexes cached in memory")
        logger.info("✓ SQLite connections pooled")
        logger.info("━" * 60)
        logger.info(f"Total startup time: {text_load_time + image_load_time + qs_load_time + chat_load_time:.3f}s")
        logger.info("Ready to accept requests!")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

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

@app.get("/api/health")
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


@app.get("/api/status")
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


# ============ CHAT ENDPOINTS ============

@app.post("/api/chat/new")
async def create_chat() -> ChatCreateResponse:
    """
    Create a new chat conversation.

    Returns:
        Chat ID and creation timestamp
    """
    try:
        chat_id = str(uuid.uuid4())
        
        # Chat will be created when first message is added
        # (or we can create it here with an empty title)
        logger.info(f"New chat created: {chat_id}")

        from datetime import datetime
        created_at = datetime.utcnow().isoformat()

        return ChatCreateResponse(
            chat_id=chat_id,
            created_at=created_at
        )

    except Exception as e:
        logger.error(f"Failed to create chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def list_conversations(limit: int = 50, offset: int = 0) -> Dict:
    """
    Get list of all conversations ordered by newest first.

    Query Parameters:
        limit: Maximum number of conversations (default: 50)
        offset: Number to skip (default: 0)

    Returns:
        List of conversation summaries with chat_id, title, created_at
    """
    try:
        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        conversations = chat_history.list_conversations(limit=limit, offset=offset)

        return {
            "status": "success",
            "count": len(conversations),
            "limit": limit,
            "offset": offset,
            "conversations": conversations
        }

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history/{chat_id}")
async def get_chat_history(chat_id: str) -> ChatHistoryResponse:
    """
    Get full conversation by chat ID.
    Returns empty messages array if chat doesn't exist (graceful fallback).

    Args:
        chat_id: Unique chat identifier

    Returns:
        Chat ID and ordered list of messages (empty if not found)
    """
    try:
        if not chat_id or not chat_id.strip():
            raise ValidationError("Chat ID cannot be empty")

        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        chat_data = chat_history.get_conversation(chat_id)
        
        # Graceful fallback: return empty messages array if chat not found
        if not chat_data:
            logger.info(f"Chat not found: {chat_id} - returning empty conversation")
            return ChatHistoryResponse(
                chat_id=chat_id,
                messages=[]
            )

        messages = []
        for msg in chat_data.get("messages", []):
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"],
                "sources": msg.get("sources")
            })

        return ChatHistoryResponse(
            chat_id=chat_id,
            messages=messages
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============ QUERY ENDPOINT ============

@app.post("/api/query")
async def query_endpoint(
    query_request: QueryRequest,
    request: Request = None,
) -> Dict:
    """
    Main RAG query endpoint supporting multi-message conversations.
    WITH DETAILED TIMING LOGS for performance debugging.

    Args:
        query_request: QueryRequest model with question and chat_id

    Returns:
        Dict with chat_id, answer, sources, and confidence score
    """
    correlation_id = request.state.correlation_id if request else str(uuid.uuid4())
    endpoint_start = time.time()

    try:
        if query_system is None:
            raise RuntimeError("Query system not initialized")
        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        question = query_request.question
        chat_id = query_request.chat_id
        top_k = settings.RETRIEVAL_TOP_K

        logger.info(f"[{correlation_id}] Query START | Chat: {chat_id} | Question: {question[:100]}...")

        # ============ CHECKPOINT 1: DB OPERATIONS ============
        db_start = time.time()

        # Verify chat exists, create if needed
        if not chat_history.conversation_exists(chat_id):
            # Create new conversation with first question as title
            title = question[:100]
            chat_history.create_conversation(chat_id, title)
            logger.debug(f"[{correlation_id}] Created new conversation: {chat_id}")

        # Add user message
        chat_history.add_message(chat_id, "user", question)

        # Get recent messages for context (last 3 pairs = 6 messages)
        chat_data = chat_history.get_conversation(chat_id)
        history_for_prompt = []
        if chat_data and chat_data.get("messages"):
            # Take last 5 messages (not including the one we just added)
            recent_msgs = chat_data["messages"][-5:]
            for msg in recent_msgs:
                history_for_prompt.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        db_time = time.time() - db_start
        logger.debug(f"[{correlation_id}] DB operations: {db_time:.3f}s")

        # ============ CHECKPOINT 2: QUERY SYSTEM EXECUTION ============
        query_system_start = time.time()
        result = query_system.query(
            question,
            top_k=top_k,
            history_messages=history_for_prompt,
        )
        query_system_time = time.time() - query_system_start
        logger.debug(f"[{correlation_id}] QuerySystem.query(): {query_system_time:.3f}s")

        answer = result.get("answer", "")
        sources = result.get("sources", [])

        # ============ CHECKPOINT 3: SAVE ASSISTANT MESSAGE ============
        save_start = time.time()
        sources_for_storage = [
            {
                "type": s.get("source_type", "unknown"),
                "source": s.get("source_file", ""),
                "score": s.get("score", 0),
            }
            for s in sources
        ]
        chat_history.add_message(chat_id, "assistant", answer, sources_for_storage)
        save_time = time.time() - save_start
        logger.debug(f"[{correlation_id}] Save assistant message: {save_time:.3f}s")

        # ============ FINAL TIMING ============
        total_endpoint_time = time.time() - endpoint_start
        logger.info(
            f"[{correlation_id}] Query COMPLETE | "
            f"DB: {db_time:.3f}s | "
            f"QuerySystem: {query_system_time:.3f}s | "
            f"Save: {save_time:.3f}s | "
            f"Total: {total_endpoint_time:.3f}s | "
            f"Confidence: {result.get('confidence', 0)}% | "
            f"Sources: {len(sources)}"
        )

        sources_response = []
        for source in sources:
            sources_response.append({
                "type": source.get("source_type", "unknown"),
                "source": source.get("source_file", ""),
                "score": source.get("score", 0),
            })

        return {
            "chat_id": chat_id,
            "answer": answer,
            "confidence": result.get("confidence", 0),
            "sources": sources_response,
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


# ============ STREAMING QUERY ENDPOINT ============

@app.post("/api/stream-query")
async def stream_query_endpoint(
    query_request: QueryRequest,
    request: Request = None,
) -> StreamingResponse:
    """
    Streaming RAG query endpoint that returns tokens progressively.
    Tokens are sent as they are generated by the LLM.

    Args:
        query_request: QueryRequest model with question and chat_id

    Returns:
        StreamingResponse with text/event-stream media type
    """
    correlation_id = request.state.correlation_id if request else str(uuid.uuid4())
    endpoint_start = time.time()

    try:
        if query_system is None:
            raise RuntimeError("Query system not initialized")
        if chat_history is None:
            raise RuntimeError("Chat history not initialized")

        question = query_request.question
        chat_id = query_request.chat_id
        top_k = settings.RETRIEVAL_TOP_K

        logger.info(f"[{correlation_id}] Stream Query START | Chat: {chat_id} | Question: {question[:100]}...")

        # ============ DB OPERATIONS ============
        db_start = time.time()

        # Verify chat exists, create if needed
        if not chat_history.conversation_exists(chat_id):
            title = question[:100]
            chat_history.create_conversation(chat_id, title)
            logger.debug(f"[{correlation_id}] Created new conversation: {chat_id}")

        # Add user message
        chat_history.add_message(chat_id, "user", question)

        # Get recent messages for context
        chat_data = chat_history.get_conversation(chat_id)
        history_for_prompt = []
        if chat_data and chat_data.get("messages"):
            recent_msgs = chat_data["messages"][-5:]
            for msg in recent_msgs:
                history_for_prompt.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        db_time = time.time() - db_start
        logger.debug(f"[{correlation_id}] DB operations: {db_time:.3f}s")

        # ============ STREAMING QUERY EXECUTION ============
        query_system_start = time.time()
        metadata, token_generator = query_system.stream_query(
            question,
            top_k=top_k,
            history_messages=history_for_prompt,
        )
        query_system_retrieval_time = time.time() - query_system_start
        logger.debug(f"[{correlation_id}] QuerySystem retrieval: {query_system_retrieval_time:.3f}s")

        # ============ CREATE STREAMING GENERATOR ============
        async def generate():
            """Generator function for streaming response."""
            # First, send metadata as JSON header
            metadata_json = {
                "type": "metadata",
                "chat_id": chat_id,
                "confidence": metadata.get("confidence", 0),
                "sources": metadata.get("sources", []),
                "retrieval_time": metadata.get("retrieval_time", 0),
            }
            yield f"data: {metadata_json}\n\n"

            # Then stream tokens
            collected_answer = ""
            try:
                for token in token_generator:
                    collected_answer += token
                    # Send token wrapped in SSE format
                    yield f"data: {token}\n\n"
                
                # Log streaming completion
                streaming_time = time.time() - endpoint_start
                logger.info(
                    f"[{correlation_id}] Stream COMPLETE | "
                    f"DB: {db_time:.3f}s | "
                    f"Retrieval: {query_system_retrieval_time:.3f}s | "
                    f"Total: {streaming_time:.3f}s | "
                    f"Answer length: {len(collected_answer)} chars | "
                    f"Confidence: {metadata.get('confidence', 0)}%"
                )

                # Save assistant message after streaming completes
                save_start = time.time()
                sources_for_storage = [
                    {
                        "type": s.get("source_type", "unknown"),
                        "source": s.get("source_file", ""),
                        "score": s.get("score", 0),
                    }
                    for s in metadata.get("sources", [])
                ]
                chat_history.add_message(chat_id, "assistant", collected_answer, sources_for_storage)
                save_time = time.time() - save_start
                logger.debug(f"[{correlation_id}] Save assistant message: {save_time:.3f}s")

                # Send completion signal
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"[{correlation_id}] Streaming error: {e}", exc_info=True)
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except ValidationError as e:
        logger.warning(f"[{correlation_id}] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RetrievalError as e:
        logger.error(f"[{correlation_id}] Retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")
    except Exception as e:
        logger.error(f"[{correlation_id}] Stream query failed: {e}", exc_info=True)
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


@app.post("/api/ingest")
async def ingest_endpoint(
    file: UploadFile = File(...),
    file_type: str = None,
    background_tasks: BackgroundTasks = None,
    request: Request = None,
) -> Dict:
    """Backward-compatible ingestion endpoint."""
    return await handle_ingest(file, file_type, background_tasks, request)


@app.post("/api/upload")
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


# ============ API INFO ENDPOINT ============

@app.get("/api/info")
async def api_info() -> Dict:
    """API information endpoint."""
    return {
        "name": "AegisRAG API",
        "version": "1.0.0",
        "description": "Fully offline multimodal RAG system",
        "endpoints": {
            "GET /api/health": "Health check",
            "GET /api/status": "System status",
            "POST /api/chat/new": "Create a new chat conversation",
            "POST /api/query": "Send message to chat (requires chat_id)",
            "GET /api/history": "List all conversations",
            "GET /api/history/{chat_id}": "Get full conversation messages",
            "POST /api/upload": "Upload and ingest a file",
            "POST /api/ingest": "Ingest a file (legacy)",
            "GET /api/files": "Get file inventory",
            "GET /api/files/search": "Search files",
        },
    }


# ============ FILE INVENTORY ENDPOINTS ============

@app.get("/api/files")
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


@app.get("/api/files/search")
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


@app.get("/api/files/{file_path:path}")
async def serve_file(file_path: str) -> FileResponse:
    """
    Serve uploaded files safely from local storage.
    Prevents directory traversal attacks by validating paths.

    Args:
        file_path: Relative file path (URL-decoded)

    Returns:
        File content as FileResponse
    """
    try:
        # Decode filename
        from urllib.parse import unquote
        filename = unquote(file_path)

        # Prevent directory traversal attacks
        if ".." in filename or filename.startswith("/"):
            raise HTTPException(status_code=403, detail="Access denied: invalid path")

        # Construct safe file path
        file_full_path = settings.UPLOADS_PATH / filename

        # Ensure file exists and is within UPLOADS_PATH
        if not file_full_path.exists():
            logger.warning(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        # Verify path is within UPLOADS_PATH (prevent directory traversal)
        try:
            file_full_path.resolve().relative_to(settings.UPLOADS_PATH.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: path outside upload directory")

        logger.info(f"Serving file: {filename}")
        return FileResponse(
            path=file_full_path,
            filename=filename,
            media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve file {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to serve file")


# ============ FRONTEND (STATIC) ============

app.mount(
    "/",
    StaticFiles(directory="frontend/insight-hub/dist", html=True),
    name="frontend",
)


# ============ MAIN ============

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
