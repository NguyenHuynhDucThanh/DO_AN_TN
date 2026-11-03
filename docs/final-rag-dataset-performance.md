# Final RAG, Dataset, Ingestion and Performance Report

## Dataset and governance

- Source: `mtue29/vietnamese-medical-dataset` on Hugging Face.
- Expected full local filename: `healthcare-backend/data/rag/raw/vietnamese-medical-dataset.json`.
- Supported source formats: JSON/JSONL, UTF-8 CSV, text-based PDF and DOCX.
- JSON is the primary large dataset source; CSV/PDF/DOCX remain available for other governed sources.
- PDF OCR is not implemented in RAG V1.
- Only `Document` records with `approval_status=APPROVED` can be ingested/re-ingested.
- Dataset files under `data/rag/raw` and derived files under `data/rag/processed` are Git ignored; `.gitkeep` preserves directories.

## Processing policy

```text
JSON → streaming loader → normalization → deduplication → chunking
     → BGE-M3 → VECTOR(1024) → PostgreSQL document_chunks + pgvector
```

For the primary dataset schema:

- `positive`: factual knowledge content used for the corpus.
- `meta`: traceability metadata such as source/article/category/title when present.
- `negative`: excluded from factual content and corpus metadata.
- `anchor`: query/evaluation support metadata; not treated as a medical fact by itself.

Re-ingestion replaces a Document's chunks in a transaction and does not intentionally accumulate duplicates. MedicalRecord and Appointment data never enter this pipeline.

## Actual dataset scope

Status: **LARGE CONTROLLED SUBSET**, not the full approximately 1 GB dataset.

| Measurement | Actual value |
| --- | ---: |
| Raw records | 400 |
| Unique article IDs | 200 |
| Unique normalized contents | 199 |
| Duplicates removed | 201 |
| New chunks / embedded chunks | 199 / 199 |
| Existing Phase 8 smoke chunks | 10 |
| Actual database benchmark corpus | 209 chunks |
| Grounded evaluation queries | 50 |
| Top-K | 5 |
| Ingestion duration | 140.286 seconds |

The full `vietnamese-medical-dataset.json` is not present and was not full-ingested. Resource usage was not measured with a fixed methodology.

## Retrieval experiment

Same Windows machine, local PostgreSQL instance, same 209-chunk corpus, BGE-M3 normalized 1024-dimensional embeddings, same 50 grounded queries and Top-K=5. Gemini generation was excluded from retrieval timing.

| Strategy | Hit@5 | Recall@5 | MRR | Mean ms | Median ms | P95 ms | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Exact Dense | 0.96 | 0.96 | 0.8447 | 5.429 | 3.370 | 6.158 | baseline/fallback |
| HNSW Dense | 0.96 | 0.96 | 0.8447 | 3.987 | 3.692 | 6.234 | **runtime default** |
| Hybrid BM25 + RRF | 0.96 | 0.96 | 0.7713 | 69.005 | 68.808 | 74.329 | experiment only |
| Hybrid + BGE Reranker | 0.98 | 0.98 | 0.8463 | 13067.815 | 8221.624 | 9935.953 | experiment only; CPU too slow |

V3 rerank mean was 12967.330 ms and the overall mean includes cold model load/download. V3's small quality improvement did not justify its multi-second CPU latency for the demo. `hnsw_dense` therefore remains final runtime strategy; complexity alone was not treated as improvement.

## Final performance summary

| Classification | Measurement | Method / sample | Result |
| --- | --- | --- | --- |
| MEASURED | Health REST | 50 sequential TestClient requests with real DB/vector check | mean 7.826 ms; median 2.875 ms; p95 3.628 ms |
| MEASURED | Exact Dense retrieval | Phase 12, 50 queries, Top-K=5 | mean 5.429 ms; median 3.370 ms; p95 6.158 ms |
| MEASURED | HNSW retrieval | Phase 12, 50 queries, ef_search=40 | mean 3.987 ms; median 3.692 ms; p95 6.234 ms |
| MEASURED | Hybrid RRF | Phase 12, 50 queries | mean 69.005 ms; median 68.808 ms; p95 74.329 ms |
| MEASURED | Hybrid reranker CPU | Phase 12, 50 queries | median 8221.624 ms; not default |
| MEASURED | Controlled ingestion | 400 raw / 199 new chunks | 140.286 seconds |
| MEASURED | Frontend largest JS chunk | Vite production build before/after lazy routes | 878.33 → 398.03 kB; gzip 269.74 → 124.41 kB |
| NOT MEASURED | Auth latency | no fixed methodology/sample | not a failure |
| NOT MEASURED | Booking latency | no fixed methodology/sample | concurrency invariant tested instead |
| NOT MEASURED | Gemini latency | external provider/quota, no fixed methodology/sample | not claimed |
| NOT MEASURED | Tool Calling latency | no fixed methodology/sample | not claimed |
| NOT MEASURED | STT latency | hardware/model/environment variation, no fixed methodology/sample | not claimed |
| KNOWN LIMITATION | Natural query `chóng mặt` | live corpus observation | retrieval can be mixed/overbroad |
| KNOWN LIMITATION | Full dataset | file absent / not ingested | controlled subset only |

These measurements describe the recorded local Windows environment and must not be generalized to every deployment.

## RAG safety explanation

For a query such as “nay mệt và sổ mũi”, the system embeds the query, retrieves relevant approved chunks and gives those sources to Gemini. The answer must use cautious language such as “những triệu chứng này có thể gặp trong…” rather than assert “bạn bị cúm”. RAG assists retrieval; it is not a diagnosis engine and does not prescribe treatment.
