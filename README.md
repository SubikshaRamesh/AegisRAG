🛡️ AegisRAG
Offline Multimodal Retrieval-Augmented Generation System

🚀 A production-oriented, fully offline multimodal RAG system that ingests documents and media, builds hybrid retrieval indexes, and serves grounded, citation-backed answers via a FastAPI backend.

📌 Overview

AegisRAG is designed for secure, offline knowledge retrieval across heterogeneous data sources.

It enables users to:

Upload and process documents and media
Perform semantic + lexical search
Generate LLM-based answers grounded in retrieved evidence
Receive citations and confidence scores
✨ Key Capabilities
🔒 Fully offline (no external APIs required)
📄 Multimodal ingestion (PDF, DOCX, Image, Audio, Video)
🧠 Hybrid retrieval:
Dense (FAISS)
BM25 lexical
Optional image retrieval (CLIP)
🔁 Reciprocal Rank Fusion (RRF) + cross-encoder reranking
📌 Citation-backed answers
📊 Confidence scoring + low-confidence guardrails
⚡ Streaming responses (SSE)
🧩 Modular, production-oriented backend
🧠 System Architecture
User Query
   ↓
Query Embedding (MiniLM)
   ↓
Hybrid Retrieval:
   • FAISS (text)
   • BM25
   • FAISS (image - CLIP)
   ↓
RRF Fusion + Filtering
   ↓
Cross-Encoder Reranking
   ↓
Context Construction
   ↓
Confidence Scoring
   ↓
LLM (GGUF via llama.cpp)
   ↓
Answer + Citations + Confidence
🔄 Data Ingestion Pipeline
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
📦 Supported Data Types
📄 PDF
📝 DOCX
🖼️ Images (OCR + optional CLIP embeddings)
🎤 Audio (transcription via Whisper)
🎥 Video (audio extraction + frame sampling)
🔍 Retrieval & Answer Pipeline
User submits query
Query is embedded using MiniLM-based model
Retrieval performed from:
FAISS (text vectors)
BM25 (lexical)
FAISS (image vectors, if applicable)
Results merged using Reciprocal Rank Fusion (RRF)
Cross-encoder reranks results
Context window constructed
Confidence score computed
If low confidence → fallback response
Else → LLM generates grounded answer
Response includes:
Answer
Sources
Confidence score
🌐 API Endpoints

Base path: /api

Core
GET /api/health
GET /api/status
GET /api/info
Chat
POST /api/chat/new
GET /api/history
GET /api/history/{chat_id}
Query
POST /api/query
POST /api/stream-query (SSE streaming)
Data
POST /api/upload
POST /api/ingest
GET /api/files
GET /api/files/search
GET /api/files/{file_path}
🗄️ Data & Storage
🧱 SQLite
Metadata
Chat history
🔍 FAISS
Text embeddings (384-dim)
Image embeddings (512-dim)
📁 Local file storage (uploads directory)
⚙️ Tech Stack
🧠 AI / ML
Sentence Transformers
OpenCLIP (multimodal embeddings)
LLaMA / Mistral (GGUF via llama-cpp-python)
Whisper (speech-to-text)
🔍 Retrieval
FAISS (CPU)
BM25
📦 Backend
FastAPI
Uvicorn
🗄️ Storage
SQLite
🛠️ Processing
pdfplumber
pytesseract
ffmpeg
🖥️ Quickstart (Local)
git clone https://github.com/your-username/AegisRAG.git
cd AegisRAG
Backend
pip install -r requirements.txt
python run.py

API runs at:

http://localhost:8000
🐳 Docker Deployment
docker-compose up --build

⚠️ Note: Update healthcheck to /api/health if needed.

🚀 Deployment Strategy
🖥️ Local Deployment
CPU-based inference
Fully offline
Ideal for development & demos
🏢 On-Premise Deployment (Target)
Secure enterprise environments
Air-gapped systems
GPU acceleration for LLM
Multi-user access
📦 Containerized Deployment
Docker + Docker Compose
Portable and reproducible
Scalable backend services
🔮 Future Development
🎥 True frame-level video retrieval (fine-grained indexing)
🧠 Improved multimodal alignment (enhanced CLIP usage)
⚡ Advanced FAISS optimization (IVF/HNSW indexing)
📊 Query analytics dashboard
👥 Authentication & role-based access
🔐 Encryption for stored data
📱 Improved frontend UX
⚙️ Distributed retrieval architecture
🧪 Testing & Verification
✅ 24+ test cases
🔍 Backend verification scripts
📊 System validation tools
⚠️ Notes
API routes are prefixed with /api/*
Some legacy docs may reference non-prefixed routes
Ensure Docker healthcheck uses /api/health
👩‍💻 Author

Subiksha Ramesh
AI Developer | RAG Systems | Multimodal AI

📄 License

This project is licensed under the MIT License.
