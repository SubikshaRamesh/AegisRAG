"""
Pydantic models for API requests and responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class QueryRequest(BaseModel):
    """Query request model."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The question to ask"
    )
    chat_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique chat identifier (UUID)"
    )

    @validator("question")
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Question cannot be empty or whitespace only")
        return v.strip()

    @validator("chat_id")
    def chat_id_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Chat ID cannot be empty or whitespace only")
        return v.strip()


class Source(BaseModel):
    """Source model for response citations."""

    type: str = Field(..., description="Type of source (pdf, image, audio, video)")
    source: str = Field(..., description="Name of the source file")
    score: float = Field(..., ge=0, le=100, description="Relevance score (0-100)")


class QueryResponse(BaseModel):
    """Query response model."""

    chat_id: str = Field(..., description="Chat identifier")
    answer: str = Field(..., description="The generated answer")
    sources: List[Source] = Field(
        default_factory=list,
        description="List of sources used to generate the answer"
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score (0-100)"
    )


class ChatCreateResponse(BaseModel):
    """Chat creation response model."""

    chat_id: str = Field(..., description="Unique chat identifier")
    created_at: str = Field(..., description="ISO timestamp")


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: float = Field(..., description="Message timestamp (unix)")
    sources: Optional[List[Source]] = Field(None, description="Message sources")


class ChatHistoryResponse(BaseModel):
    """Chat history response model."""

    chat_id: str = Field(..., description="Chat identifier")
    messages: List[ChatMessage] = Field(..., description="Ordered messages in conversation")


class ConversationSummary(BaseModel):
    """Conversation summary for list endpoint."""

    chat_id: str = Field(..., description="Chat identifier")
    title: str = Field(..., description="First user message (truncated)")
    created_at: str = Field(..., description="ISO timestamp")


class IngestionResponse(BaseModel):
    """Ingestion response model."""

    status: str = Field(..., description="Status (success/error)")
    filename: str = Field(..., description="Name of uploaded file")
    file_type: str = Field(..., description="Type of file (pdf, image, audio, video, docx)")
    chunks_created: int = Field(..., ge=0, description="Number of chunks created")
    message: str = Field(..., description="Status message")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status (healthy/unhealthy/unavailable)")
    text_vectors: int = Field(default=0, description="Number of text vectors in store")
    image_vectors: int = Field(default=0, description="Number of image vectors in store")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class StatusResponse(BaseModel):
    """System status response model."""

    status: str = Field(..., description="System status")
    text_embedder: str = Field(..., description="Text embedding model")
    clip_embedder: str = Field(..., description="Image embedding model")
    llm_model: str = Field(..., description="LLM model path")
    text_vectors: int = Field(..., description="Number of text vectors")
    image_vectors: int = Field(..., description="Number of image vectors")
    vector_dim: Dict[str, int] = Field(..., description="Embedding dimensions")


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: Optional[str] = Field(None, description="Timestamp of error")
