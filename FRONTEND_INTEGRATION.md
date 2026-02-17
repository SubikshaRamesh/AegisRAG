# AegisRAG Production Backend - Integration Guide

**Version**: 1.0  
**Date**: February 17, 2026  
**Status**: ✅ **PRODUCTION READY**

---

## Quick Start for Frontend Integration

### API Base URL
```
http://localhost:8000  (Development)
http://your-server:8000  (Production)
```

### Required Dependencies Installation
```bash
pip install fastapi uvicorn python-dotenv pydantic
# Or run: python install_backend.py
```

### Start Backend
```bash
# Development (with auto-reload)
python run.py

# Production
uvicorn api.server:app --host 0.0.0.0 --port 8000

# Docker
docker-compose up -d
```

---

## 🔌 API Endpoints for Frontend

### 1. POST /query - Get Answers from Knowledge Base

**Request:**
```typescript
fetch('http://localhost:8000/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'What is in the documents?',
    top_k: 3  // Optional, default 3
  })
})
```

**Response:**
```json
{
  "answer": "The documents contain information about...",
  "citations": [
    {
      "source_type": "pdf",
      "source_file": "document.pdf",
      "page_number": 5,
      "timestamp": null
    }
  ],
  "confidence": 85.5,
  "processing_time_seconds": 8.32
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request (empty question, invalid top_k)
- `500` - Server error

---

### 2. POST /ingest - Upload & Process Files

**Request:**
```typescript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('file_type', 'pdf');  // Optional, auto-detected

fetch('http://localhost:8000/ingest', {
  method: 'POST',
  body: formData
})
```

**Supported File Types:**
- `pdf` - PDF documents
- `docx` - Word documents  
- `image` - JPG, PNG, GIF, BMP (with OCR)
- `audio` - MP3, WAV, M4A, FLAC (with transcription)
- `video` - MP4, AVI, MOV, MKV (audio + frames)

**Response:**
```json
{
  "status": "success",
  "filename": "document.pdf",
  "file_type": "pdf",
  "chunks_extracted": 42,
  "chunks_added": 40,
  "duplicates_skipped": 2,
  "processing_time_seconds": 12.5,
  "message": "Successfully ingested 40 new chunks from document.pdf"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request (invalid file type, file too large)
- `500` - Server error

---

### 3. GET /health - Health Check

**Request:**
```typescript
fetch('http://localhost:8000/health')
```

**Response:**
```json
{
  "status": "healthy",
  "text_vectors": 1250,
  "image_vectors": 350
}
```

Use for liveness probes and monitoring.

---

### 4. GET /status - System Information

**Request:**
```typescript
fetch('http://localhost:8000/status')
```

**Response:**
```json
{
  "status": "running",
  "text_embedder": "MiniLM-L6-v2",
  "clip_embedder": "OpenAI CLIP",
  "llm_model": "./models/tinyllama.gguf",
  "text_vectors": 1250,
  "image_vectors": 350,
  "vector_dim": {
    "text": 384,
    "image": 512
  }
}
```

---

## 📊 Response Time Expectations

| Endpoint | Typical Time | Notes |
|----------|--------------|-------|
| /health | <10ms | Instant health check |
| /status | <50ms | System info lookup |
| /query | 10-30s | Includes LLM inference (CPU) |
| /ingest (PDF) | 5-30s | Depends on file size |
| /ingest (Video) | 30-120s | Includes audio transcription + frame extraction |

---

## 🔒 Production Stability Features

### ✅ Thread-Safe Concurrent Operations
- Multiple users can upload files simultaneously
- FAISS index protected with RLock
- No race conditions on concurrent writes

### ✅ Duplicate Detection
- Same file uploaded twice = no duplicate vectors
- Automatic chunk deduplication
- Response shows `duplicates_skipped` count

### ✅ Request Tracking
- Every request gets unique correlation ID
- Trace full request lifecycle in logs
- Structured performance metrics

### ✅ Model Efficiency
- Embedding models loaded ONCE at startup
- No model reloading on each request
- 5-10x faster ingestion vs naive implementation

### ✅ Transaction Safety
- SQLite operations use ACID transactions
- Rollback on errors
- No data loss on crashes

### ✅ Clean Error Responses
- Structured JSON error messages
- HTTP status codes for programmatic handling
- Correlation IDs in responses

---

## 🐛 Error Handling

### Example Error Response
```json
{
  "detail": "File too large: 600.0MB (max: 500MB)"
}
```

### Common Error Cases

**400 Bad Request**
```typescript
// Empty question
POST /query?question=
// Response: {"detail": "Question cannot be empty"}

// Invalid top_k
POST /query?question=test&top_k=100
// Response: {"detail": "top_k must be between 1 and 10"}

// Unsupported file type
POST /ingest with .exe file
// Response: {"detail": "Unsupported file type: .exe"}
```

**503 Service Unavailable**
```typescript
// System still initializing
GET /health
// Response: {"status": "unavailable", "message": "System initializing..."}
```

**500 Internal Server Error**
```typescript
// Server error (check logs)
// Response: {"detail": "Internal server error"}
```

---

## 📝 Frontend Integration Examples

### React Example
```typescript
import { useState } from 'react';

export function QueryComponent() {
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const query = async (question: string) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 3 })
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail);
      }
      
      const data = await res.json();
      setAnswer(data.answer);
    } catch (error) {
      console.error('Query failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input 
        type="text" 
        onKeyPress={(e) => e.key === 'Enter' && query(e.target.value)}
      />
      {loading && <p>Loading...</p>}
      {answer && <p>{answer}</p>}
    </div>
  );
}
```

### File Upload Example
```typescript
export function UploadComponent() {
  const [progress, setProgress] = useState('');

  const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    setProgress('Uploading...');
    
    try {
      const res = await fetch('http://localhost:8000/ingest', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      setProgress(
        `✅ ${data.chunks_added} chunks added, ` +
        `${data.duplicates_skipped} duplicates skipped`
      );
    } catch (error) {
      setProgress('❌ Upload failed');
    }
  };

  return (
    <div>
      <input 
        type="file" 
        onChange={(e) => e.target.files && uploadFile(e.target.files[0])} 
      />
      <p>{progress}</p>
    </div>
  );
}
```

---

## 🚀 Deployment Options

### Option 1: Local Development
```bash
python run.py
# Server at http://127.0.0.1:8000
```

### Option 2: Production Server
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option 3: Docker
```bash
docker-compose up -d
# Server at http://localhost:8000
# Logs: docker-compose logs -f aegisrag
```

---

## 🔧 Configuration

### Environment Variables
```bash
# .env file
AEGIS_HOST=0.0.0.0
AEGIS_PORT=8000
AEGIS_DEBUG=false
AEGIS_LOG_LEVEL=INFO

# Retrieval settings
RETRIEVAL_TOP_K=3
FAISS_DISTANCE_THRESHOLD=1.0

# Upload limits
MAX_UPLOAD_SIZE_MB=500

# LLM settings
LLM_MAX_TOKENS=120
LLM_TEMPERATURE=0.0
LLM_THREADS=12
```

---

## 📊 Monitoring & Logs

### Check System Status
```bash
curl http://localhost:8000/status
```

### Check Health
```bash
curl http://localhost:8000/health
```

### View Logs (Docker)
```bash
docker-compose logs -f aegisrag
```

### Log Format
```
[correlation-id] INFO: Query: What is...
[correlation-id] INFO: Query complete - confidence: 85.5%, sources: 3, elapsed: 8.25s
```

---

## 🐛 Troubleshooting

### Backend Won't Start
```
ERROR: No module named 'fastapi'
SOLUTION: pip install fastapi uvicorn
```

### Empty Results
```
Response: {"answer": "Information not found in knowledge base."}
SOLUTION: Ingest documents first with POST /ingest
```

### Slow Responses
```
SOLUTION: 
  - Reduce RETRIEVAL_TOP_K
  - Decrease LLM_MAX_TOKENS
  - Increase LLM_THREADS
```

### Upload Fails
```
ERROR: File too large
SOLUTION: Increase MAX_UPLOAD_SIZE_MB in .env
```

---

## ✅ Integration Checklist

Before connecting frontend:

- [ ] Backend starts successfully (`python run.py`)
- [ ] Health check returns 200 (`curl http://localhost:8000/health`)
- [ ] Test query works (`curl -X POST http://localhost:8000/query?question=test`)
- [ ] Test upload works (`curl -X POST http://localhost:8000/ingest -F file=@test.pdf`)
- [ ] CORS allows your frontend origin
- [ ] Environment variables configured
- [ ] Model files exist in `models/` directory

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc
- **Production Audit Report**: `PRODUCTION_FIXES.md`
- **Configuration Guide**: `BACKEND_README.md`

---

## 🎯 Key Takeaways for Frontend Team

1. **Query Endpoint** (`POST /query`) - Use for all search queries
2. **Ingest Endpoint** (`POST /ingest`) - Use for file uploads
3. **Response Times** - Queries take 10-30s (LLM inference on CPU)
4. **Error Handling** - Check HTTP status codes, parse JSON errors
5. **Parallel Uploads** - Safe for concurrent users
6. **Duplicate Files** - Handled automatically, won't corrupt index
7. **Performance Metrics** - All responses include `processing_time_seconds`

---

**Backend Status**: ✅ PRODUCTION READY  
**Integration Ready**: ✅ YES  
**Contact**: Check `PRODUCTION_FIXES.md` for audit details
