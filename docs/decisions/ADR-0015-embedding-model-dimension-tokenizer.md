# ADR-0015: HuggingFace embedding model, vector dimension, and chunking tokenizer

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Phase 2 (chunking, embeddings, duplicate-Topic detection); Phase 3 (Critic duplicate check); Phase 8 (Tutor retrieval, grounding and lockdown thresholds)
- **SRS refs:** FR-CON-002; Section 17 "Chunking" and "Embedding" rows; FR-CUR-002; BUS-021; BUS-050; FR-QB-003; FR-TUT-002; FR-TUT-003; Section 26 "Threshold governance"; Section 31.2 ContentChunk ("vector/model version"); Section 33; Section 45

## Context
- Section 17 requires "the configured HuggingFace embedding model", with its
  model and version recorded, and vectors stored in pgvector. It does not
  name a model.
- FR-CON-002 requires chunks of **at most 800 embedding-model tokens with a
  120-token overlap**. Chunk length is therefore measured with the embedding
  model's own tokenizer, so the tokenizer depends on the model choice and is
  decided here.
- The same model is used for duplicate-Topic detection (initial threshold
  `>0.92`), Critic duplicate checks, Tutor grounding (`0.70`), and lockdown
  (`0.85`). Under BUS-050, every threshold is stored with the model version
  and must be revalidated before a new model version becomes active.
- A pgvector column has a fixed dimension. Changing to a model with a
  different dimension needs a migration and a full re-embed. That makes this
  decision expensive to reverse.
- **Hard constraint:** the model must embed a whole 800-token chunk. A model
  with a 512-token limit silently truncates the last ~290 tokens of a full
  chunk. Retrieval would then miss text that the citation claims the chunk
  contains.

## Options

### A. `BAAI/bge-m3` (recommended)
- 1024-dim dense vectors, 8192-token input limit, XLM-RoBERTa tokenizer, MIT
  licence. Loads through `sentence-transformers` without
  `trust_remote_code`.
- **Pros:** An 800-token chunk fits easily. Strong retrieval quality. No
  query/document prefixes to get wrong. Also handles non-English text if any
  appears in Indian syllabus material.
- **Cons:** About 568M parameters (~2.3 GB in float32), so CPU embedding is
  slower than small models. That is acceptable for batch Celery ingestion,
  but the per-query Tutor embedding latency should be measured in Phase 8.

### B. `nomic-ai/nomic-embed-text-v1.5`
- 768-dim vectors (can be truncated to smaller sizes), 8192-token limit,
  BERT tokenizer, Apache-2.0 licence.
- **Pros:** Smaller and faster than bge-m3, with long context.
- **Cons:** Needs `trust_remote_code=True`, which runs Python code
  downloaded from the model repository inside the backend. That conflicts
  with the Section 36 security baseline unless the revision is pinned and
  audited. It also needs task prefixes (`search_document:` /
  `search_query:`), and if one is forgotten, similarity scores and every
  threshold calibrated on them are silently wrong.

### C. `BAAI/bge-base-en-v1.5` (or `all-MiniLM-L6-v2`)
- 768 or 384 dims, small and fast on CPU.
- **Cons:** The input limit is 512 tokens (MiniLM: 256). Full 800-token
  chunks would be truncated, which fails the hard constraint above. This
  option is listed only to show why a small model is not chosen.

### How the model runs (applies to every option)
- **Locally in the celery/backend container (recommended):** uses
  `sentence-transformers` (which brings `transformers` and a CPU-only
  PyTorch wheel). Model weights at a pinned revision hash are cached in a
  Docker volume. Course content never leaves the deployment.
- **HuggingFace Inference API:** no PyTorch in the image, but all uploaded
  course content would go to an external service, and results depend on a
  remote model that could change. This conflicts with Section 33's
  reproducibility requirement and the data-minimisation intent of Section
  32 and NFR-SEC-011.

## Recommendation
- **Model:** `BAAI/bge-m3` at a pinned HuggingFace revision (commit hash),
  dense output only, `normalize_embeddings=True`, cosine similarity.
- **Vector dimension:** `vector(1024)` in pgvector. This is within
  pgvector's 2000-dimension limit for HNSW/IVFFlat indexes on `vector`.
- **Tokenizer for chunking:** bge-m3's own tokenizer, loaded with
  `transformers.AutoTokenizer` from the **same pinned revision**. Chunk
  boundaries are counted in its tokens: at most 800 per chunk, 120 overlap.
- **Runtime:** local inference on CPU, with weights cached in a Docker
  volume. The Inference API is not used.

Why:
1. It is the only option that meets the 800-token requirement **and** loads
   without running remote code.
2. Using one pinned revision for both the tokenizer and the model means the
   "800 embedding-model tokens" in chunking is exactly what the model sees,
   and the recorded model version (Section 17) describes both.
3. Running locally keeps the pipeline reproducible and keeps course content
   inside the deployment.

## Consequences if accepted
- `sentence-transformers` is added, which also brings `transformers` and
  PyTorch. A **CPU-only** PyTorch wheel is required to keep image size
  reasonable. This is the largest dependency in Phase 2 and needs explicit
  human sign-off as an addition beyond the fixed stack.
- Every ContentChunk stores the embedding configuration version: model id,
  revision hash, dimension, and normalisation. Retrieval and similarity
  checks only compare vectors with the same configuration version.
- The initial thresholds in the SRS (`0.92`, `0.70`, `0.85`) are not assumed
  to suit bge-m3. Under BUS-050 and Section 26 they must be checked against a
  validation set before activation. The Phase 2 plan has to define that set
  for the `0.92` duplicate threshold. Phase 3 and Phase 8 handle their own
  thresholds.
- A later change of model is a new configuration version. If the dimension
  changes, it needs a migration and a re-embed, under a new ADR that
  supersedes this one.
