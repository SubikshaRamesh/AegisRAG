# Performance Optimization & Debugging Guide

## Problem Statement
- **Direct LLM inference**: ~0.9 seconds ✅ (fast)
- **RAG API call**: 60-90 seconds ❌ (slow)
- **Root cause**: RAG pipeline bottleneck (NOT the LLM itself)

## Solution: Comprehensive Performance Logging

### What Was Added

#### 1. **Server Startup Verification** (`api/server.py`)
```
✓ QuerySystem is GLOBAL singleton (NOT recreated per request)
✓ query_system.text_embedder: {ID} (ONCE created at startup)
✓ query_system.llm: {ID} (ONCE created at startup)
✓ All models LOCKED in memory (no reload per request)
✓ FAISS indexes cached in memory
✓ SQLite connections pooled
```

**Log Output Example:**
```
[INFO] INITIALIZATION COMPLETE - PERFORMANCE CHECKLIST
[INFO] ✓ QuerySystem is GLOBAL singleton (ID: 140234567890)
[INFO] ✓ query_system.text_embedder: 140234567891 (ONCE created)
[INFO] ✓ query_system.llm: 140234567892 (ONCE created)
[INFO] ✓ All models LOCKED in memory (no reload per request)
[INFO] ✓ FAISS indexes cached in memory
[INFO] ✓ SQLite connections pooled
[INFO] Total startup time: 45.234s
[INFO] Ready to accept requests!
```

#### 2. **Detailed API Endpoint Timing** (`api/server.py`)
Checkpoint-based timing in `/api/query` endpoint:

```
[INFO] Query START | Chat: {chat_id} | Question: {question[:100]}...
[DEBUG] DB operations: {time}s
[DEBUG] QuerySystem.query(): {time}s
[DEBUG] Save assistant message: {time}s
[INFO] Query COMPLETE | DB: {db_time}s | QuerySystem: {qs_time}s | Save: {save_time}s | Total: {total_time}s | Confidence: {conf}% | Sources: {count}
```

**Example Metrics Mapping:**
```
Total time = DB + QuerySystem + Save
If Total > 5s:
  - If QuerySystem > 3s → investigate embedding/FAISS/LLM
  - If DB > 1s → check SQLite queries
  - If Save > 1s → check chat history storage
```

#### 3. **QuerySystem Fine-Grained Timing** (`core/pipeline/query_system.py`)
Detailed breakdown of all pipeline stages:

```
[INFO] [QUERY] START - Question: {question[:80]}...
[DEBUG] [QUERY] Text embedding: {time}s
[DEBUG] [QUERY] Text FAISS search: {time}s ({count} results)
[DEBUG] [QUERY] CLIP embedding: {time}s  [IF MULTIMODAL]
[DEBUG] [QUERY] Image FAISS search: {time}s ({count} results) [IF MULTIMODAL]
[DEBUG] [QUERY] Combined X text + Y image = Z total results
[DEBUG] [QUERY] Selected top K chunks
[DEBUG] [QUERY] DB fetch: {time}s ({count} chunks)
[DEBUG] [QUERY] Context build: {time}s ({total_chars} total chars)
[DEBUG] [QUERY] LLM generation: {time}s
[DEBUG] [QUERY] Confidence: {score}%
[INFO] [QUERY] COMPLETE in {total_time}s | Embed: {e}s | TextSearch: {t}s | ImageSearch: {i}s | DB: {d}s | Context: {c}s | LLM: {l}s | Confidence: {conf}%
```

**QuerySystem Breakdown:**
```
Total QuerySystem time = Embed + TextSearch + ImageSearch + DB + Context + LLM

Expected times (with optimizations):
- Text embedding: 0.1-0.3s
- Text FAISS search: 0.05-0.1s
- CLIP embedding: 0.5-1.0s (ONLY if multimodal keywords detected)
- Image FAISS search: 0.05-0.1s (ONLY if multimodal)
- DB fetch: 0.01-0.05s (depends on SQLite)
- Context build: <0.01s
- LLM generation: 0.5-2.0s

Target: Total QuerySystem < 3–4 seconds
```

#### 4. **LLM Generation Detailed Logs** (`core/llm/generator.py`)
Breakdown of LLM-specific operations:

```
[INFO] [LLM] Model loaded in {time}s
[DEBUG] [LLM] Language detection: {time}s (detected: {lang})
[DEBUG] [LLM] Context build: {time}s ({char_count} chars)
[DEBUG] [LLM] Prompt build: {time}s ({prompt_length} chars)
[DEBUG] [LLM] Model inference: {time}s
[INFO] [LLM] generate_answer complete: {total_time}s (lang: {t}s, context: {t}s, prompt: {t}s, inference: {t}s)
```

**LLM Breakdown:**
```
Total LLM time = Language detection + Context build + Prompt build + Inference

Expected:
- Language detection: <0.01s
- Context build: <0.01s
- Prompt build: <0.01s
- Inference: 0.5-2.0s (this is the bottleneck, unavoidable with OfflineLLM)

If inference > 3s → model is too slow or n_threads/batch_size needs tuning
```

---

## How to Debug Performance Issues

### Step 1: Identify Bottleneck
Check logs after making a query:

```
[INFO] Query COMPLETE | DB: 0.05s | QuerySystem: 3.5s | Save: 0.02s | Total: 3.57s
```

**If Total > 5 seconds:**

### Step 2: Drill Down by Component

**A. If QuerySystem > 4s:**
```
[INFO] [QUERY] COMPLETE in 4.2s | 
  Embed: 0.15s | 
  TextSearch: 0.08s | 
  ImageSearch: 0.00s | 
  DB: 0.02s | 
  Context: 0.00s | 
  LLM: 3.9s ← CULPRIT
```
→ **Problem: LLM inference time** → needs model optimization

**B. If Embed time > 0.5s:**
```
[DEBUG] [QUERY] Text embedding: 0.62s ← HIGH
```
→ **Problem: SentenceTransformer too slow** → check device (CPU vs GPU), model size

**C. If FAISS search > 0.5s:**
```
[DEBUG] [QUERY] Text FAISS search: 0.55s ← HIGH
```
→ **Problem: FAISS index too large** → implement filtering or index optimization

**D. If DB fetch > 0.1s:**
```
[DEBUG] [QUERY] DB fetch: 0.12s ← HIGH
```
→ **Problem: SQLite query slow** → add indexes, optimize queries

### Step 3: Verify No Model Reloading

Check startup logs for object IDs:
```
[INFO] query_system.text_embedder: 140234567891 (ONCE created)
[INFO] query_system.llm: 140234567892 (ONCE created)
```

Then make 3 queries and check that IDs remain the same in logs:
```
Query 1: [INIT] EmbeddingGenerator created (ID: 140234567891) ✓ SAME
Query 2: [INIT] EmbeddingGenerator created (ID: 140234567891) ✓ SAME
Query 3: [INIT] EmbeddingGenerator created (ID: 140234567891) ✓ SAME
```

If IDs change → models are being reloaded (BAD)

---

## Performance Optimization Checklist

- ✅ QuerySystem initialized ONCE at startup (global singleton)
- ✅ EmbeddingGenerator loaded ONCE (shared instance)
- ✅ OfflineLLM loaded ONCE (shared instance)
- ✅ FAISS indexes cached in memory
- ✅ Detailed timing logs at every stage
- ✅ Conditional multimodal search (skip CLIP if no keywords)
- ✅ Context trimmed to 400 characters (reduced LLM load)
- ✅ top_k reduced from 3 → 2 (fewer embeddings, faster retrieval)
- ✅ No language re-generation (single LLM call)
- ✅ Correlation IDs for request tracing

---

## Expected Performance After Optimization

### Scenario 1: Text-Only Query (No Multimodal)
```
Total: ~1-2 seconds
├─ Embedding: 0.15s
├─ Text FAISS: 0.08s
├─ DB fetch: 0.02s
└─ LLM generation: 0.5-1.5s
```

### Scenario 2: Query with Multimodal Keywords
```
Total: ~2-3 seconds
├─ Text Embedding: 0.15s
├─ Text FAISS: 0.08s
├─ CLIP Embedding: 0.7s
├─ Image FAISS: 0.08s
├─ DB fetch: 0.02s
└─ LLM generation: 0.8-1.5s
```

### Scenario 3: If Experiencing Slowness
1. **Check total time**: If < 3s → acceptable
2. **Check LLM time**: If > 2s → optimize model parameters
3. **Check embedding time**: If > 0.5s → verify GPU usage or reduce model size
4. **Check FAISS time**: If > 0.2s → profile index size

---

## Log Filtering for Production

To reduce log verbosity, adjust log level:
```python
# In config/settings.py or logger.py
logging.basicConfig(level=logging.INFO)  # Hide DEBUG logs
```

**INFO logs will show:**
- Query START/COMPLETE
- Total timings
- Errors

**DEBUG logs will show:**
- Component-level timings
- Object IDs
- Detailed breakdowns

---

## Next Steps if Still Slow

If even with these optimizations you see **> 5 second latency**:

1. **Check CPU/GPU utilization** → is model being bottlenecked?
2. **Profile the LLM model** → consider smaller model (tinyllama vs phi-3)
3. **Batch requests** → process multiple queries in parallel
4. **Cache embedding results** → avoid re-embedding same queries
5. **Optimize FAISS** → use GPU-accelerated FAISS if available

See [PRODUCTION_AUDIT.md](PRODUCTION_AUDIT.md) for further tuning strategies.
