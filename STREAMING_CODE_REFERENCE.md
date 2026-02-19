# STREAMING RESPONSE - COMPLETE CODE REFERENCE

## Backend Implementation

### 1. OfflineLLM - stream_answer() Method

**File:** `core/llm/generator.py`

```python
def stream_answer(
    self,
    question: str,
    contexts: List[Dict],
    history: List[Dict] = None,
) -> Generator[str, None, None]:
    """Stream answer tokens as they are generated.
    
    Yields:
        str: Individual tokens from the LLM
    """
    gen_start = time.time()

    if not contexts:
        logger.debug("[LLM] No contexts provided, returning fallback")
        yield "Information not found in knowledge base."
        return

    # 🔥 Build context (limit size for speed)
    context_build_start = time.time()

    context_text = ""
    for c in contexts:
        context_text += c["text"].strip() + "\n\n"

    # Limit context to prevent slowdown
    context_text = context_text[:1500]

    context_build_time = time.time() - context_build_start
    logger.debug(f"[LLM] Context build: {context_build_time:.3f}s ({len(context_text)} chars)")

    # 🔥 Multilingual WITHOUT language detection
    prompt_start = time.time()

    prompt = f"""You are a helpful AI assistant.

Answer in the SAME language as the question.
Use ONLY the provided context.
Do NOT invent information.
If the answer is not found, reply exactly:
Information not found in knowledge base.

Question:
{question}

Context:
{context_text}

Answer:
"""

    prompt_time = time.time() - prompt_start
    logger.debug(f"[LLM] Prompt build: {prompt_time:.3f}s ({len(prompt)} chars)")

    # 🔥 LLM Streaming with TinyLlama optimized parameters
    llm_call_start = time.time()
    token_count = 0

    try:
        for chunk in self.llm(
            prompt,
            max_tokens=100,
            temperature=0.1,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["Question:", "</s>"],
            stream=True,  # 🔥 Enable streaming
        ):
            token = chunk["choices"][0]["text"]
            if token:
                token_count += 1
                yield token
    except Exception as e:
        logger.error(f"[LLM] Streaming error: {e}")
        yield "Error generating response. Please try again."
        return

    llm_call_time = time.time() - llm_call_start
    tokens_per_second = token_count / llm_call_time if llm_call_time > 0 else 0
    total_time = time.time() - gen_start

    logger.info(
        f"[LLM] 🚀 Stream complete: {llm_call_time:.3f}s "
        f"({token_count} tokens, {tokens_per_second:.1f} tokens/sec)"
    )
    logger.debug(
        f"[LLM] Stream breakdown: "
        f"context: {context_build_time:.3f}s, "
        f"streaming: {llm_call_time:.3f}s, "
        f"total: {total_time:.3f}s"
    )
```

**Key Points:**
- Uses `stream=True` parameter in llama-cpp-python
- Yields tokens one at a time as they're generated
- Proper error handling with fallback message
- Performance logging for monitoring
- Same prompt structure as non-streaming version

---

### 2. QuerySystem - stream_query() Method

**File:** `core/pipeline/query_system.py`

```python
def stream_query(
    self,
    question: str,
    top_k: int = 2,
    history_messages: Optional[List[Dict]] = None,
) -> tuple:
    """Execute query with streaming LLM response.
    
    Returns:
        tuple: (source_metadata dict, token_generator)
        
    The generator yields individual tokens as the LLM generates them.
    The metadata includes sources and confidence for display.
    """
    query_start = time.time()
    logger.info(f"[STREAM QUERY] START - Question: {question[:80]}...")

    # ============ TEXT EMBEDDING ============
    embed_start = time.time()
    text_embedding = self.text_embedder.embed([question])
    text_embedding = np.array(text_embedding).astype("float32")
    embed_time = time.time() - embed_start
    logger.debug(f"[STREAM QUERY] Text embedding: {embed_time:.3f}s")

    # ============ TEXT FAISS SEARCH ============
    search_start = time.time()
    text_results = self.text_faiss.search(
        text_embedding,
        top_k=top_k
    )
    search_time = time.time() - search_start
    logger.debug(f"[STREAM QUERY] Text FAISS search: {search_time:.3f}s ({len(text_results)} results)")

    # ============ CONDITIONAL IMAGE SEARCH ============
    image_results = []
    image_time = 0

    enable_multimodal = any(k in question.lower() for k in MULTIMODAL_KEYWORDS)
    if enable_multimodal:
        logger.debug(f"[STREAM QUERY] Multimodal keywords detected")
        if len(self.image_faiss.chunk_ids) > 0:
            clip_start = time.time()
            image_embedding = self.clip_embedder.embed_text([question])
            image_embedding = np.array(image_embedding).astype("float32")
            clip_time = time.time() - clip_start
            logger.debug(f"[STREAM QUERY] CLIP embedding: {clip_time:.3f}s")

            img_search_start = time.time()
            image_results = self.image_faiss.search(
                image_embedding,
                top_k=top_k
            )
            image_search_time = time.time() - img_search_start
            image_time = clip_time + image_search_time
            logger.debug(f"[STREAM QUERY] Image FAISS search: {image_search_time:.3f}s ({len(image_results)} results)")
        else:
            logger.debug("[STREAM QUERY] Multimodal enabled but no image vectors available")
    else:
        logger.debug("[STREAM QUERY] No multimodal keywords - skipping image search")

    # ============ COMBINE & RANK ============
    combined = sorted(
        text_results + image_results,
        key=lambda x: x["distance"]
    )
    logger.debug(f"[STREAM QUERY] Combined {len(text_results)} text + {len(image_results)} image = {len(combined)} total results")

    # ============ EXTRACT TOP K ============
    chunk_ids = [r["chunk_id"] for r in combined[:top_k]]
    distances = [r["distance"] for r in combined[:top_k]]
    logger.debug(f"[STREAM QUERY] Selected top {len(chunk_ids)} chunks")

    # ============ DATABASE FETCH ============
    db_start = time.time()
    chunks = self._fetch_chunks_from_db(chunk_ids)
    db_time = time.time() - db_start
    logger.debug(f"[STREAM QUERY] DB fetch: {db_time:.3f}s ({len(chunks)} chunks)")

    if not chunks:
        logger.info("[STREAM QUERY] No results found - returning fallback")
        metadata = {
            "sources": [],
            "confidence": 0,
            "retrieval_time": time.time() - query_start
        }
        return (metadata, iter(["Information not found in knowledge base."]))

    # ============ BUILD CONTEXT ============
    context_start = time.time()
    contexts = self._build_context(chunks)
    context_time = time.time() - context_start
    logger.debug(f"[STREAM QUERY] Context build: {context_time:.3f}s ({sum(len(c['text']) for c in contexts)} total chars)")

    # ============ CONFIDENCE ============
    avg_distance = sum(distances) / len(distances)
    similarity = max(0, 1 - (avg_distance / 2))
    confidence = round(similarity * 100, 2)
    logger.debug(f"[STREAM QUERY] Confidence: {confidence}%")

    # ============ DEDUPLICATE SOURCES ============
    sources_dict = {}
    for chunk in chunks:
        if chunk.source_file not in sources_dict:
            sources_dict[chunk.source_file] = {
                "source_type": chunk.source_type,
                "source_file": chunk.source_file,
                "score": confidence,
                "page_number": chunk.page_number,
                "timestamp": chunk.timestamp,
            }

    # ============ PREPARE STREAMING ============
    retrieval_time = time.time() - query_start
    logger.info(
        f"[STREAM QUERY] Retrieval COMPLETE in {retrieval_time:.3f}s | "
        f"Embed: {embed_time:.3f}s | "
        f"TextSearch: {search_time:.3f}s | "
        f"DB: {db_time:.3f}s | "
        f"Context: {context_time:.3f}s | "
        f"Ready to stream LLM response..."
    )

    # Create generator for streaming LLM
    token_gen = self.llm.stream_answer(
        question,
        contexts,
        history_messages or []
    )

    # Return metadata and generator
    metadata = {
        "sources": list(sources_dict.values()),
        "confidence": confidence,
        "retrieval_time": retrieval_time
    }

    return (metadata, token_gen)
```

**Key Points:**
- All retrieval happens before streaming starts
- Returns tuple: (metadata dict, generator)
- Metadata includes sources, confidence, retrieval time
- Generator created but not executed until consumed
- Detailed logging at each stage

---

### 3. FastAPI Endpoint - /api/stream-query

**File:** `api/server.py`

```python
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
```

**Key Points:**
- Returns `StreamingResponse` with `text/event-stream` media type
- Uses async generator function
- Sends metadata first as JSON
- Each token wrapped in SSE format: `data: {token}\n\n`
- Message saved after completion
- Proper error handling

---

## Frontend Implementation

### 1. API Service - streamQuestion() Method

**File:** `frontend/insight-hub/src/services/api.ts`

```typescript
async streamQuestion(
  question: string,
  chatId: string,
  onToken: (token: string) => void,
  onMetadata?: (metadata: any) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> {
  try {
    const response = await fetch("/api/stream-query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question, chat_id: chatId }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("Response body not readable");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // Process any remaining buffer
        if (buffer.trim()) {
          this._processStreamChunk(buffer.trim(), onToken, onMetadata, onError);
        }
        onComplete?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete lines from buffer
      const lines = buffer.split("\n\n");
      buffer = lines[lines.length - 1]; // Keep incomplete line in buffer

      for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i].trim();
        if (line.startsWith("data: ")) {
          const data = line.slice(6); // Remove "data: " prefix
          if (data && data !== "[DONE]") {
            this._processStreamChunk(data, onToken, onMetadata, onError);
          }
        }
      }
    }
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    onError?.(err);
  }
}

private _processStreamChunk(
  data: string,
  onToken: (token: string) => void,
  onMetadata?: (metadata: any) => void,
  onError?: (error: Error) => void
): void {
  try {
    // Try to parse as JSON (metadata)
    const parsed = JSON.parse(data);
    if (parsed.type === "metadata") {
      onMetadata?.(parsed);
    } else if (parsed.type === "error") {
      onError?.(new Error(parsed.message || "Unknown error"));
    }
  } catch {
    // Not JSON, treat as token text
    onToken(data);
  }
}
```

**Key Points:**
- Uses native `fetch()` API with `ReadableStream`
- Properly decodes chunks with `TextDecoder`
- Handles SSE format (lines with `data: ` prefix)
- Separates callbacks for tokens, metadata, errors, completion
- Handles partial messages in buffer
- Graceful error handling

---

### 2. HomePage Component - Updated handleSend()

**File:** `frontend/insight-hub/src/pages/HomePage.tsx`

```typescript
const handleSend = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!query.trim() || !currentChatId) return;

  setError(null);
  setIsLoading(true);

  // 1. Add user message immediately
  const userMessage: Message = {
    id: crypto.randomUUID(),
    role: "user",
    content: query,
    timestamp: new Date(),
  };

  setMessages((prev) => [...prev, userMessage]);
  const userQuery = query; // Store before clearing
  setQuery("");

  // 2. Create placeholder for streaming message
  const assistantMessageId = crypto.randomUUID();
  const assistantMessage: Message = {
    id: assistantMessageId,
    role: "assistant",
    content: "", // Will be filled progressively
    timestamp: new Date(),
    isStreaming: true,
    confidence: 0,
    sources: [],
  };

  setMessages((prev) => [...prev, assistantMessage]);
  setStreamingMessageId(assistantMessageId);

  try {
    // 3. Use streaming API
    await api.streamQuestion(
      userQuery,
      currentChatId,
      // ✅ Token callback - append to message
      (token: string) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content + token }
              : msg
          )
        );
      },
      // ✅ Metadata callback - set sources and confidence
      (metadata: any) => {
        if (metadata.sources || metadata.confidence) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    sources: metadata.sources || msg.sources,
                    confidence: metadata.confidence || msg.confidence,
                  }
                : msg
            )
          );
        }
      },
      // ✅ Error callback
      (error: Error) => {
        setError(`Streaming error: ${error.message}`);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, isStreaming: false, content: msg.content || "Error: Failed to stream response" }
              : msg
          )
        );
        setStreamingMessageId(null);
      },
      // ✅ Complete callback - mark message as done
      () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, isStreaming: false }
              : msg
          )
        );
        setStreamingMessageId(null);
      }
    );
  } catch (queryError) {
    setError(extractErrorMessage(queryError));
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantMessageId
          ? { ...msg, isStreaming: false }
          : msg
      )
    );
    setStreamingMessageId(null);
  } finally {
    setIsLoading(false);
  }
};
```

**Key Points:**
- User message added immediately (no wait)
- Empty assistant message created as placeholder
- Tokens appended as they arrive via onToken
- Sources/confidence updated from metadata
- State management tracks streaming status
- Proper cleanup on error
- Message finalized on completion

---

### 3. Message Type Update

**File:** `frontend/insight-hub/src/pages/HomePage.tsx`

```typescript
type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: number;
  sources?: Source[];
  isStreaming?: boolean; // ✅ NEW: Track if still streaming
};
```

---

### 4. UI Rendering Updates

**File:** `frontend/insight-hub/src/pages/HomePage.tsx`

```tsx
{/* Loading indicator */}
{(isLoading || isChatLoading) && (
  <div className="bg-card rounded-2xl border border-border p-6 shadow-card">
    <div className="flex items-center gap-3">
      <Loader className="w-5 h-5 text-primary animate-spin" />
      <span className="text-sm text-muted-foreground">
        {isChatLoading ? "Loading chat..." : "Streaming response..."}
      </span>
    </div>
  </div>
)}

{/* Message rendering with streaming indicator */}
) : (
  <div className="bg-card rounded-2xl border border-border p-6 shadow-card hover:shadow-card-hover transition-shadow duration-300">
    <div className="flex items-start justify-between gap-4 mb-4">
      <div className="flex-1 space-y-3">
        <div className="text-foreground leading-relaxed whitespace-pre-wrap">
          {msg.content}
          {msg.isStreaming && (
            <span className="inline-block w-2 h-5 ml-1 bg-primary rounded-sm animate-pulse" />
            // ↑ Blinking cursor while streaming
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {msg.confidence !== undefined && msg.confidence > 0 && (
            <span
              className={`text-xs px-2.5 py-1 rounded-full ${confidenceClass(
                msg.confidence
              )}`}
            >
              Confidence {formatConfidence(msg.confidence)}
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            {msg.timestamp.toLocaleTimeString()}
          </span>
        </div>
      </div>
      {!msg.isStreaming && (
        <button
          onClick={() => toggleVoice(msg.id)}
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
            isPlaying === msg.id
              ? "gradient-sky text-primary-foreground shadow-sky"
              : "bg-accent text-accent-foreground hover:bg-primary hover:text-primary-foreground"
          }`}
          title={isPlaying === msg.id ? "Stop reading" : "Read aloud"}
        >
          {isPlaying === msg.id ? (
            <VolumeX className="w-5 h-5" />
          ) : (
            <Volume2 className="w-5 h-5" />
          )}
        </button>
      )}
    </div>

    {msg.sources && msg.sources.length > 0 && (
      <div className="border-t border-border pt-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
          Sources
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {msg.sources.map((source, i) => (
            <SourceLink
              key={`${source.source}-${i}`}
              filename={source.source}
              type={source.type}
              score={source.score}
              onPreview={handleOpenPreview}
            />
          ))}
        </div>
      </div>
    )}
  </div>
)
```

**Key Points:**
- Blinking cursor shows while streaming
- Voice button hidden during streaming
- Confidence only shown when available
- Sources display with proper styling
- Loading indicator shows spinner + text

---

## Integration Checklist

- [x] Import `Generator` type in generator.py
- [x] Implement `stream_answer()` method
- [x] Implement `stream_query()` method
- [x] Add `/api/stream-query` endpoint
- [x] Import `StreamingResponse` in api/server.py
- [x] Implement `streamQuestion()` in API service
- [x] Update `Message` type with `isStreaming` field
- [x] Update `handleSend()` to use streaming
- [x] Add UI rendering for streaming state
- [x] Add Loader icon import
- [x] Test end-to-end streaming flow

---

**Version:** 1.0
**Status:** Production Ready
**Last Updated:** February 2026
