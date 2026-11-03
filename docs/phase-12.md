# Phase 12 — RAG V2/V3 Experiments

Ngày nghiệm thu: 29/10/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

SRS v1.1 là source of truth. Phase 12 chỉ mở rộng retrieval strategy và thực hiện benchmark; không thay đổi SRS, business logic, Voice/Handoff architecture hoặc roadmap và không bắt đầu Phase 13.

## 1. Audit và phạm vi reuse

### ALREADY IMPLEMENTED — REUSED

- Document/DocumentChunk, approval workflow và ingestion pipeline Phase 8.
- JSON/CSV/PDF/DOCX loader, normalize, deduplicate và chunking.
- BGE-M3 embedding 1024 chiều và PostgreSQL + pgvector.
- RAG V1 exact dense, GeminiClient, ChatOrchestrator và source traceability.
- HNSW cosine index `ix_document_chunks_embedding_hnsw` từ schema hiện có.
- MedicalRecord privacy boundary và AI failure isolation Phase 8–11.

### PARTIALLY IMPLEMENTED — EXTENDED

- Dataset downloader được mở rộng bằng chế độ deterministic large subset.
- Evaluation được mở rộng từ 4 smoke query thành 50 grounded query.
- RAGService nhận strategy thông qua một factory/config tập trung.
- Metrics được mở rộng với mean/median/p95 latency và reranking latency.

### NEW IN PHASE 12

- `HnswDenseRetriever`.
- Unicode-aware `Bm25Retriever` trên cùng corpus PostgreSQL.
- Deterministic RRF và `HybridRrfRetriever`.
- `BgeReranker` và `HybridRerankRetriever`.
- Production fallback về exact dense; experiment mode không che lỗi.
- Script benchmark chung xuất JSON/CSV.

Không có RAG service, Document module, vector store hoặc chatbot thứ hai.

## 2. Corpus benchmark

Trạng thái: **LARGE CONTROLLED SUBSET**, không phải full dataset.

Nguồn chính là `mtue29/vietnamese-medical-dataset`. Downloader dùng API rows chính thức, lấy deterministic range `[0, 400)`, nên có thể tái lập bằng cùng lệnh và tham số.

| Chỉ số | Số liệu thật |
| --- | ---: |
| Raw records | 400 |
| Unique article IDs | 200 |
| Unique contents sau normalize/dedup | 199 |
| Duplicates removed | 201 |
| Chunks tạo mới | 199 |
| Chunks embedded | 199 |
| Ingestion duration | 140,286 giây |
| Document benchmark | `7800d74f-d7ad-4b73-b550-5ed1679b523f` |

Database development còn 10 smoke chunks của Phase 8. Vì vậy corpus thật mà mọi strategy cùng truy vấn khi benchmark gồm **209 chunks**: 199 chunks large subset + 10 chunks smoke cũ. Large subset là corpus benchmark chính; 10 smoke chunks chiếm khoảng 4,8% và không có strategy nào được dùng corpus khác.

Một output cũ trong terminal từng gắn nhãn `FULL_INGESTION_PASS` do logic nhận diện tên file `.large-` chưa đúng. Đây chỉ là lỗi nhãn output, không phải full ingestion; script đã được sửa và toàn bộ tài liệu ghi đúng **LARGE CONTROLLED SUBSET**.

## 3. Baseline được cố định

Các yếu tố sau được giữ nguyên cho bốn strategy:

- Corpus/chunks: cùng 209 chunks trong PostgreSQL tại thời điểm benchmark.
- Embedding: `BAAI/bge-m3`, normalized vector, dimension 1024.
- Query set: 50 câu tiếng Việt từ mapping `anchor → article_id` cố định.
- Ground truth: `expected_article_id` của chính article nguồn.
- Final Top-K: 5.
- Máy và PostgreSQL instance: cùng máy Windows development.
- Generation/Gemini: không chạy trong retrieval benchmark; do đó không có LLM-as-judge hoặc answer-level metric bị trình bày như ground truth.

Query embedding được tính một lần và reuse giữa các dense strategy nhằm tránh chênh lệch do thời gian encode. Metrics retrieval là Hit@5, Recall@5 và MRR. Latency đo bằng `perf_counter`, báo mean/median/p95. Kết quả không được suy rộng thành đánh giá lâm sàng.

## 4. Strategy và cấu hình

### V1 — Exact Dense

Question → BGE-M3 → exact cosine search → Top-K. Transaction đặt `enable_indexscan=off` và EXPLAIN xác nhận không chọn HNSW.

### HNSW Dense

Question → BGE-M3 → HNSW cosine index → Top-K. `ef_search=40`; EXPLAIN xác nhận dùng index `ix_document_chunks_embedding_hnsw`.

### V2 — Hybrid BM25 + RRF

- Dense candidates: 20 qua HNSW.
- Sparse candidates: 20 qua BM25.
- BM25: `k1=1,5`, `b=0,75`.
- Tokenization: Unicode NFC + casefold + token chữ/số Unicode; không bỏ dấu tiếng Việt.
- Fusion: deterministic RRF với `rrf_k=60`.
- Final Top-K: 5.

BM25 đọc đúng các chunk APPROVED + COMPLETED trong PostgreSQL, không tạo knowledge base riêng.

### V3 — Hybrid + BGE Reranker

- Candidate generation: V2.
- Candidate size rerank: 20.
- Model: `BAAI/bge-reranker-v2-m3`.
- Device: CPU; batch size 4.
- Final Top-K: 5.

Reranker không chạy trên toàn corpus. Benchmark V3 bao gồm cold model download/load trong mean; median/p95 phản ánh các query sau khi model đã load.

## 5. Kết quả thật

| Strategy | Hit@5 | Recall@5 | MRR | Mean ms | Median ms | P95 ms | Rerank mean ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V1 Exact Dense | 0,96 | 0,96 | 0,8447 | 5,429 | 3,370 | 6,158 | 0 |
| HNSW Dense | 0,96 | 0,96 | 0,8447 | 3,987 | 3,692 | 6,234 | 0 |
| V2 Hybrid RRF | 0,96 | 0,96 | 0,7713 | 69,005 | 68,808 | 74,329 | 0 |
| V3 Hybrid + Reranker | 0,98 | 0,98 | 0,8463 | 13.067,815 | 8.221,624 | 9.935,953 | 12.967,330 |

V2 không cải thiện Hit/Recall và làm MRR thấp hơn baseline trên query set hiện tại. V3 tăng Hit/Recall thêm 0,02 và MRR thêm khoảng 0,0017 so với exact/HNSW, nhưng CPU reranking có median khoảng 8,2 giây; mean cao hơn vì gồm cold model load/download. Không có answer-level metric vì Phase 12 chưa có methodology LLM-as-judge đủ đáng tin để coi như ground truth.

## 6. Quyết định cuối

**Final strategy: `hnsw_dense`.**

Lý do:

- Giữ nguyên Hit@5, Recall@5 và MRR của exact baseline trên 50 query.
- Mean retrieval latency thấp nhất trong phép đo này.
- Dùng index/schema sẵn có, không thêm database hay migration.
- Ít CPU/RAM và ít failure mode hơn V2/V3.
- Phù hợp demo Windows hơn reranker CPU có độ trễ nhiều giây.

Exact dense được giữ làm baseline và fallback. V2/V3 vẫn nằm trong code để test, báo cáo và thí nghiệm tiếp theo, nhưng không được mặc định là tốt hơn chỉ vì phức tạp hơn.

## 7. Failure isolation và privacy

- Production factory fallback về exact dense khi HNSW/BM25/reranker lỗi.
- Experiment mode tắt fallback để benchmark không che lỗi.
- Business MVP hoạt động độc lập với AI/RAG.
- Dense, BM25, reranker và evaluation chỉ dùng Document/DocumentChunk APPROVED + COMPLETED.
- MedicalRecord không xuất hiện trong corpus, candidate, evaluation set, Gemini context hoặc Tool Calling.
- Source metadata được giữ qua dense, RRF và reranking.

## 8. Files

### Tạo mới

- `healthcare-backend/app/rag/factory.py`.
- `healthcare-backend/app/rag/evaluation_phase12.json`.
- `healthcare-backend/scripts/build_rag_evaluation.py`.
- `healthcare-backend/scripts/evaluate_rag_phase12.py`.
- `healthcare-backend/tests/test_phase12_rag_strategies.py`.
- `healthcare-backend/tests/test_phase12_rag_integration.py`.
- `docs/phase-12.md` và `docs/phase-12-results.json/.csv`.

### Mở rộng

- `app/rag/retrieval.py`, `service.py`, `schemas.py`, `evaluation.py`.
- `app/ai/router.py`, `app/core/config.py`.
- `scripts/download_rag_dataset.py`, `scripts/ingest_rag_dataset.py`.
- `.env.example`, Backend README và requirement traceability.

Frontend không cần sửa vì strategy thay đổi sau cùng một API/RAG pipeline hiện có.

## 9. Database và migration

- Không thay schema.
- Không tạo/sửa migration.
- Alembic `current` và `heads`: `0004_add_json_document_type (head)`.
- `pip check`: không có dependency hỏng.

## 10. Kiểm thử thật

| Kiểm tra | Kết quả |
| --- | --- |
| Backend không bật DB integration | 111 passed, 41 skipped đúng điều kiện |
| Backend + PostgreSQL integration | 152 passed |
| Exact plan | PASS |
| HNSW index plan | PASS |
| BM25 Unicode/empty/ranking | PASS |
| RRF overlap/dense-only/sparse-only/deterministic | PASS |
| Reranker ordering/Top-K/empty/failure | PASS |
| Source/fallback/MedicalRecord isolation | PASS |
| Frontend Vitest | 37 passed |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; chỉ có cảnh báo chunk size không chặn build |
| Python compileall / pip check | PASS |

## 11. Hạn chế

- 400 records/199 chunks unique là large controlled subset, không phải full dataset.
- Evaluation dùng 50 anchor-derived query và một positive article mỗi query; chưa phải bộ đánh giá chuyên gia y khoa.
- Corpus nhỏ nên lợi ích scaling của HNSW chưa thể hiện đầy đủ.
- BM25 hiện tokenize đơn giản, chưa word-segmentation tiếng Việt.
- Reranker CPU quá chậm cho demo; GPU hoặc model nhỏ hơn có thể được nghiên cứu sau.
- Chưa có answer-level evaluation/LLM-as-judge.
- Chất lượng STT tiếng Việt Phase 11 vẫn là known limitation riêng, không được tuning trong Phase 12.

## 12. Kết luận

**PHASE 12: PASS.**

**LARGE CONTROLLED CORPUS BENCHMARK PASS.**

Phase 13 chưa được bắt đầu.
