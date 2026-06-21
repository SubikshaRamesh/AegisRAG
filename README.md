# 🛡️ AegisRAG
### Local-First Multimodal Retrieval-Augmented Generation System

🚀 A local-first multimodal RAG system that ingests documents and media, builds hybrid retrieval indexes, and serves grounded, citation-backed answers via a FastAPI backend and React frontend.

---

## 📌 Overview

AegisRAG is designed for **secure, local-first knowledge retrieval** across heterogeneous data sources.

It enables users to:

- Upload and process documents and media
- Perform semantic + lexical search
- Generate LLM-based answers grounded in retrieved evidence
- Receive citations and confidence scores

> **Note:** AegisRAG supports local LLM inference via GGUF models through `llama-cpp-python`, so no external API calls are required when configured this way. A fully verified, air-gapped offline deployment has not been tested, so we describe the system as "local-first" rather than "fully offline."

---

## 🆕 Recent Improvements

**Backend**

- Shared embedding model loading — SentenceTransformer and CLIP models are loaded once and reused, instead of being reloaded on every ingestion/query call
- Dependency injection of shared embedders into `QuerySystem` and `IngestionManager`
- Confidence scoring improvements for summary-style questions and single-document retrieval
- Source metadata enrichment (filename, score, page number, snippet)
- Streaming query endpoint (`/api/stream-query`) using Server-Sent Events (SSE)
- SQLite optimization — removed duplicate chunk fetches and unnecessary DB lookups

**Frontend**

- Streaming chat UI that consumes the SSE stream and displays tokens progressively
- Source citation display below answers
- Confidence score display in the UI
- Chat history support (conversations stored and reloaded)
- UUID compatibility fix — `generateId()` utility replacing `crypto.randomUUID()`
- Frontend integration with:
  - `/api/query`
  - `/api/stream-query`
  - `/api/history`
  - `/api/chat/new`

---

## 📸 Project Preview

### 💬 Chat Interface
<p align="center">
  <img src="images/chat.png" width="900"/>
</p>
<p align="center">
  Ask questions and receive grounded answers with citations and confidence scores.
</p>

---

### 📤 Upload & Ingestion
<p align="center">
  <img src="images/upload.png" width="900"/>
</p>
<p align="center">
  Upload documents and media for processing and indexing into the knowledge base.
</p>

---

### 🕘 Chat History
<p align="center">
  <img src="images/history.png" width="900"/>
</p>
<p align="center">
  View past conversations and maintain contextual query sessions.
</p>

---

### 📄 Document Explorer
<p align="center">
  <img src="images/documents.png" width="900"/>
</p>
<p align="center">
  Browse, search, and manage ingested files and indexed content.
</p>

---

## ✨ Key Capabilities

- 📄 Multimodal ingestion (PDF, DOCX, Image, Audio, Video)
- 🧠 Hybrid retrieval:
  - Dense (FAISS)
  - BM25 lexical
  - Optional image retrieval (CLIP)
- 🔁 Reciprocal Rank Fusion (RRF)
- 🎯 Cross-encoder reranking
- 📌 Citation-backed answers
- 📊 Confidence scoring
- ⚡ Streaming responses (SSE)
- 🗂️ Chat history
- 📦 FastAPI backend
- 🖥️ React frontend

---

## 🧠 System Architecture

```

User
↓
React Frontend
↓
FastAPI Backend
↓
Query System
↓
Hybrid Retrieval
• FAISS
• BM25
• CLIP
↓
Reciprocal Rank Fusion (RRF)
↓
Cross Encoder Reranker
↓
Context Construction
↓
Confidence Scoring
↓
LLM
↓
Answer + Sources + Confidence

```

---

## 🔄 Data Ingestion Pipeline

```

Upload Files (PDF / DOCX / Image / Audio / Video)
↓
Content Extraction:
• PDF/DOC parsing
• OCR (images)
• Speech-to-text (audio/video)
• Frame extraction (video)
↓
Chunking
↓
Embedding Generation:
• Text → Sentence Transformers (384-dim)
• Image → CLIP (512-dim)
↓
Storage:
• FAISS (vectors)
• SQLite (metadata + chat history)

````

---

## 📦 Supported Data Types

- 📄 PDF
- 📝 DOCX
- 🖼️ Images (OCR + optional CLIP embeddings)
- 🎤 Audio (transcription via Whisper)
- 🎥 Video (audio extraction + frame sampling)

---

## 🔍 Retrieval & Answer Pipeline

1. User submits query
2. Query embedded using MiniLM
3. Retrieval performed from:
   - FAISS (text vectors)
   - BM25 (lexical)
   - FAISS (image vectors, if applicable)
4. Results merged using **Reciprocal Rank Fusion (RRF)**
5. Cross-encoder reranks results
6. Context window constructed
7. Confidence score computed
8. If low confidence → fallback response
9. Else → LLM generates grounded answer

### Response Includes:
- Answer
- Sources
- Confidence score

---

## 🌐 API Endpoints

**Base path:** `/api`

### Core
- `GET /api/health`
- `GET /api/status`
- `GET /api/info`

### Chat
- `POST /api/chat/new`
- `GET /api/history`
- `GET /api/history/{chat_id}`

### Query
- `POST /api/query`
- `POST /api/stream-query` (SSE streaming)

### Data
- `POST /api/upload`
- `POST /api/ingest`
- `GET /api/files`
- `GET /api/files/search`
- `GET /api/files/{file_path}`

---

## 🗄️ Data & Storage

### 🧱 SQLite
- Metadata
- Chat history

### 🔍 FAISS
- Text embeddings (384-dim)
- Image embeddings (512-dim)

### 📁 Local Storage
- Uploaded files

---

## ⚙️ Tech Stack

### 🧠 AI / ML
- Sentence Transformers
- OpenCLIP (multimodal embeddings)
- LLaMA / Mistral (GGUF via llama-cpp-python)
- Whisper (speech-to-text)

### 🔍 Retrieval
- FAISS (CPU)
- BM25

### 📦 Backend
- FastAPI
- Uvicorn

### 🖥️ Frontend
- React
- TypeScript

### 🗄️ Storage
- SQLite

### 🛠️ Processing
- pdfplumber
- pytesseract
- ffmpeg

---

## 🖥️ Quickstart (Local)

```bash
git clone https://github.com/SubikshaRamesh/AegisRAG.git
cd AegisRAG
````

### Backend

```bash
pip install -r requirements.txt
python run.py
```

API runs at:

```
http://localhost:8000
```

---

## 🐳 Docker

```bash
docker-compose up --build
```

⚠️ Ensure healthcheck uses:

```
/api/health
```

**Status:**
- ✅ Dockerfile created
- ✅ Docker Compose configuration created
- ✅ Backend verified locally
- ✅ Frontend verified locally
- ⏳ Docker runtime validation in progress

---

## 🔮 Future Development

* 🎥 Frame-level video retrieval
* 🧠 Improved multimodal alignment
* ⚡ Advanced FAISS optimization (IVF/HNSW)
* 📊 Analytics / query insights dashboard
* 👥 Authentication & RBAC
* 🔐 Data encryption
* 📱 Enhanced frontend UX
* ⚙️ Distributed retrieval
* 🏢 On-premise / air-gapped deployment
* 🏢 Enterprise deployment support
* ☁️ AWS deployment
* 🐳 Docker validation completion

---

## 🧪 Testing & Verification

Testing performed:

* Document ingestion testing
* Query processing testing
* Hybrid retrieval testing
* Streaming response testing
* Chat history testing
* Frontend-backend integration testing
* Citation generation testing
* Confidence scoring testing

A comprehensive automated test suite is planned for future releases.

---

## ⚠️ Notes

* All API routes are prefixed with `/api/*`
* Some legacy docs may reference non-prefixed routes
* Ensure Docker healthcheck uses `/api/health`
* "Local-first" applies when configured to use a local GGUF model; a fully air-gapped deployment has not been verified

---

## 👩‍💻 Author

## Subiksha R
AI Developer | Retrieval-Augmented Generation (RAG) | Multimodal AI Systems

---

## 📄 License

This project is licensed under the **MIT License**.
