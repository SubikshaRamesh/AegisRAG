# Streaming Response - Example Usage & Testing

## Quick Start Example

### Backend Usage (Python)

```python
# Using QuerySystem with streaming
from core.pipeline.query_system import QuerySystem

# Initialize system (already done at startup)
query_system = QuerySystem(
    text_faiss=text_faiss_manager,
    image_faiss=image_faiss_manager,
    model_path="models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"
)

# Execute streaming query
question = "What is in the document?"
metadata, token_generator = query_system.stream_query(question)

# Process tokens
for token in token_generator:
    print(token, end="", flush=True)  # Print as received

# After loop, metadata contains:
print(f"\nSources: {metadata['sources']}")
print(f"Confidence: {metadata['confidence']}%")
print(f"Retrieval time: {metadata['retrieval_time']:.2f}s")
```

### FastAPI Usage

The streaming endpoint is automatically exposed:

```bash
curl -X POST http://localhost:8000/api/stream-query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is in the document?", "chat_id": "chat-123"}'
```

**Response (Server-Sent Events):**
```
data: {"type":"metadata","chat_id":"chat-123","confidence":85,"sources":[...],"retrieval_time":1.234}

data: The
data:  document
data:  contains
...
data: [DONE]
```

### Frontend Usage (React/TypeScript)

#### Option 1: Using the API Service (Recommended)

```typescript
import { api } from "@/services/api";

// In your component
const handleStreamingQuery = async () => {
  let fullAnswer = "";
  let currentSources: Source[] = [];

  try {
    await api.streamQuestion(
      "What is in the document?",
      "chat-123",
      
      // On each token
      (token) => {
        fullAnswer += token;
        console.log("Token:", token);
        setAnswer(fullAnswer); // Update UI
      },
      
      // On metadata (sources, confidence)
      (metadata) => {
        console.log("Sources:", metadata.sources);
        console.log("Confidence:", metadata.confidence);
        currentSources = metadata.sources;
        setConfidence(metadata.confidence);
      },
      
      // On error
      (error) => {
        console.error("Stream error:", error);
        setError(error.message);
      },
      
      // On complete
      () => {
        console.log("Streaming complete!");
        saveMessageToHistory(fullAnswer, currentSources);
      }
    );
  } catch (err) {
    console.error("Failed to stream:", err);
  }
};
```

#### Option 2: Direct Fetch (Advanced)

```typescript
// For more control over the streaming process
const response = await fetch("/api/stream-query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "...", chat_id: "..." })
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value, { stream: true });
  // Process SSE format: "data: ..."
  if (chunk.startsWith("data: ")) {
    const data = chunk.slice(6);
    console.log("Token:", data);
  }
}
```

## Real-World Examples

### Example 1: Chat Interface

```typescript
const ChatComponent = () => {
  const [messages, setMessages] = useState<Message[]>([]);

  const sendMessage = async (userQuestion: string) => {
    // 1. Add user message
    setMessages(prev => [...prev, {
      role: "user",
      content: userQuestion,
      timestamp: new Date()
    }]);

    // 2. Create streaming message
    const msgId = Date.now();
    const emptyAssistantMsg = {
      id: msgId,
      role: "assistant",
      content: "",
      isStreaming: true
    };
    setMessages(prev => [...prev, emptyAssistantMsg]);

    // 3. Stream response
    await api.streamQuestion(
      userQuestion,
      chatId,
      
      // Update content as tokens arrive
      (token) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === msgId
              ? { ...msg, content: msg.content + token }
              : msg
          )
        );
      },
      
      // Add sources
      (metadata) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === msgId
              ? { ...msg, sources: metadata.sources }
              : msg
          )
        );
      },
      
      null, // error handler
      
      // Mark complete
      () => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === msgId
              ? { ...msg, isStreaming: false }
              : msg
          )
        );
      }
    );
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={msg.role}>
            {msg.content}
            {msg.isStreaming && <Cursor />}
          </div>
        ))}
      </div>
      <input
        onKeyPress={(e) => e.key === "Enter" && sendMessage(e.target.value)}
      />
    </div>
  );
};
```

### Example 2: Collecting Full Response

```typescript
// Collect the entire streamed response
const fullResponse = await new Promise<string>((resolve) => {
  let answer = "";
  
  api.streamQuestion(
    question,
    chatId,
    (token) => { answer += token; },
    undefined,
    undefined,
    () => { resolve(answer); }  // Resolve with full answer
  );
});

console.log("Full response:", fullResponse);
```

### Example 3: Measuring Performance

```typescript
const measureStreamingPerformance = async () => {
  const start = Date.now();
  let tokenCount = 0;
  let retrievalTime = 0;
  
  await api.streamQuestion(
    question,
    chatId,
    
    (token) => {
      tokenCount++;
    },
    
    (metadata) => {
      retrievalTime = metadata.retrieval_time;
      console.log(`Retrieval took ${retrievalTime.toFixed(2)}s`);
    },
    
    (error) => console.error(error),
    
    () => {
      const totalTime = (Date.now() - start) / 1000;
      const streamTime = totalTime - retrievalTime;
      const tokensPerSec = tokenCount / streamTime;
      
      console.log(`Performance:
        - Retrieval: ${retrievalTime.toFixed(2)}s
        - Streaming: ${streamTime.toFixed(2)}s
        - Total: ${totalTime.toFixed(2)}s
        - Tokens: ${tokenCount}
        - Speed: ${tokensPerSec.toFixed(1)} tokens/sec
      `);
    }
  );
};
```

## Testing Scenarios

### Test 1: Basic Streaming

```bash
# Terminal 1: Start server
python run.py

# Terminal 2: Test with curl
curl -X POST http://localhost:8000/api/stream-query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the document about?","chat_id":"test-1"}' \
  -N  # Important: disable buffering
```

**Expected Output:**
```
data: {"type":"metadata",...}

data: This
data:  document
data:  is
data:  about
...
data: [DONE]
```

### Test 2: High Load

```python
import asyncio
import aiohttp

async def stream_query_concurrent(question, chat_id):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/stream-query",
            json={"question": question, "chat_id": chat_id}
        ) as resp:
            async for chunk in resp.content.iter_any():
                print(chunk.decode(), end="", flush=True)

# Run 5 concurrent streams
tasks = [
    stream_query_concurrent("Question 1", f"chat-{i}")
    for i in range(5)
]
await asyncio.gather(*tasks)
```

### Test 3: Frontend Integration

```typescript
// In React component
test("streaming updates UI progressively", async () => {
  const { getByText } = render(<ChatComponent />);
  
  // Simulate user sending message
  fireEvent.click(getByText("Send"));
  
  // Verify user message appears
  expect(getByText("Show me the answer")).toBeInTheDocument();
  
  // Wait for sources to appear
  await waitFor(() => {
    expect(getByText(/Sources/i)).toBeInTheDocument();
  });
  
  // Wait for answer to complete
  await waitFor(() => {
    expect(getByText(/The answer is/i)).toBeInTheDocument();
  });
});
```

### Test 4: Error Recovery

```typescript
// Test what happens when stream fails mid-response
const testErrorRecovery = async () => {
  let partialAnswer = "";
  
  try {
    await api.streamQuestion(
      question,
      chatId,
      (token) => { partialAnswer += token; },
      null,
      (error) => {
        console.log(`Error after ${partialAnswer.length} chars:`, error);
        // Could implement retry logic here
      }
    );
  } catch (err) {
    console.log("Stream connection lost:", err);
    console.log("Partial answer saved:", partialAnswer);
  }
};
```

## Debugging Tips

### Check Backend Streaming

```bash
# Monitor logs for streaming operations
tail -f logs/aegisrag.log | grep -E "\[STREAM|tokens/sec"

# Expected output:
# [STREAM QUERY] START - Question: What is...
# [STREAM QUERY] Retrieval COMPLETE in 1.234s
# [LLM] 🚀 Stream complete: 3.456s (78 tokens, 22.6 tokens/sec)
# [STREAM] Stream COMPLETE | DB: 0.234s | Retrieval: 1.234s | Total: 4.789s
```

### Check Frontend Streaming

```typescript
// Add debug logging to component
const handleStreamingDebug = async () => {
  console.time("Stream Total");
  
  await api.streamQuestion(
    question,
    chatId,
    (token) => {
      console.debug("Token:", JSON.stringify(token));
    },
    (metadata) => {
      console.log("Metadata received:", metadata);
    },
    (error) => {
      console.error("Stream error:", error);
    },
    () => {
      console.timeEnd("Stream Total");
    }
  );
};
```

### Check Network Stream

In Browser DevTools:

1. Open **Network** tab
2. Filter by `stream-query`
3. Click the request
4. Go to **Response** tab
5. View SSE messages in real-time

Expected:
```
data: {"type":"metadata",...}

data: The
data:  answer
data:  text
...
```

### Performance Profiling

```python
# Backend: Enable detailed timing
import logging
logging.getLogger('core.pipeline').setLevel(logging.DEBUG)

# Frontend: React Profiler
import { Profiler } from 'react';

<Profiler id="streaming-comp" onRender={onRenderCallback}>
  <ChatComponent />
</Profiler>
```

## Comparison: Before vs After

### Before (Non-Streaming)

```
[Client] POST /api/query
    ↓
[Server] Process retrieval + LLM
    ⏳ Wait 20 seconds
    ↓
[Server] Return full JSON response
    ↓
[Client] Display answer
```

**User Experience:**
- Blank screen for 20 seconds
- Then answer suddenly appears
- Feel of slowness and waiting

### After (Streaming)

```
[Client] POST /api/stream-query
    ↓
[Server] Process retrieval
    ↓
[Server] Send metadata (sources, confidence)
    ⏱️ 1-2 seconds
    ↓
[Server] Start streaming tokens
    ↓
[Client] Display sources immediately
[Client] Show first tokens in 1-2 sec
[Client] Watch answer type out (2-6 sec)
    ↓
[Server] Send [DONE]
    ↓
[Client] Save complete message
```

**User Experience:**
- Immediate feedback within 1 second
- See sources while reading answer starting
- Animated typing effect (ChatGPT-like)
- Feels natural and engaging
- **Perceived time: 4-8 seconds** (vs 20 seconds)

---

## Next Steps

1. **Test in Production:**
   ```bash
   pytest tests/test_streaming.py -v
   ```

2. **Monitor Performance:**
   ```bash
   python scripts/benchmark_streaming.py
   ```

3. **Gather Metrics:**
   - Average tokens/second
   - Retrieval time distribution
   - Error rate during streaming
   - User satisfaction metrics

---

**Last Updated:** February 2026
**Version:** 1.0
