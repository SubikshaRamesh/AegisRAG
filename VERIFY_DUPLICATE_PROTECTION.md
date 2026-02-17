# Duplicate Protection Verification Guide

## Step-by-step (manual)

### Step 1: Delete existing FAISS and SQLite data

```powershell
cd c:\Users\de\Desktop\AegisRAG

Remove-Item -Force -ErrorAction SilentlyContinue workspaces\default\storage\metadata\faiss.index
Remove-Item -Force -ErrorAction SilentlyContinue workspaces\default\storage\metadata\chunk_ids.pkl
Remove-Item -Force -ErrorAction SilentlyContinue workspaces\default\storage\metadata\chunks.db
```

### Step 2: Run first ingestion

```powershell
python -c "from core.ingestion.ingestion_manager import ingest; ingest('workspaces/default/uploads/sample.pdf', 'pdf', 'sample')"
```

### Step 3: Verify FAISS count (first time)

```powershell
python -m tests.verify_faiss_persistence
```

**Expected:** `index.ntotal` ≈ 275 (or similar, depending on PDF).

### Step 4: Run second ingestion (same file)

```powershell
python -c "from core.ingestion.ingestion_manager import ingest; ingest('workspaces/default/uploads/sample.pdf', 'pdf', 'sample')"
```

### Step 5: Verify FAISS count (second time)

```powershell
python -m tests.verify_faiss_persistence
```

**Expected:** `index.ntotal` should be **unchanged** (no duplicates added).

---

## One-shot script

Or run the full verification in one go:

```powershell
python tests/verify_duplicate_protection.py
```

---

## If duplicate protection fails

1. **Chunk IDs differ between runs**  
   Check that `pdf_ingest.py` uses deterministic IDs:
   `{source_file}_page{page_number}_chunk{chunk_index}`

2. **Different `file_path` each time**  
   Use the exact same path both runs (e.g. `workspaces/default/uploads/sample.pdf`).

3. **FAISS not loading from disk**  
   Ensure `faiss.index` and `chunk_ids.pkl` exist before the second ingestion.
