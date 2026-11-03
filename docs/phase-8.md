# Phase 8 — RAG V1

Ngày nghiệm thu: 23/10/2026. SRS v1.1 là source of truth; SRS và roadmap không bị sửa. Phase 8 mở rộng Document module và Gemini chatbot hiện có, không tạo model/table/service tương đương thứ hai và không triển khai Phase 9.

## Phân loại trước implementation

| Nhóm | Kết quả audit |
| --- | --- |
| ALREADY IMPLEMENTED / REUSED | Document metadata + Admin APPROVE/REJECT; DocumentChunk 1:N; `VECTOR(1024)`; HNSW cosine; ingestion states; GeminiClient/ChatService/Chat UI; auth/RBAC; MedicalRecord isolation. |
| PARTIALLY IMPLEMENTED / EXTENDED | DocumentService/Router chưa ingestion; file type chưa có JSON; Chat response chưa có sources; chatbot chưa retrieval. |
| NOT IMPLEMENTED / NEW | Loader JSON/CSV/PDF/DOCX; normalization/dedup/chunking; BGE-M3 adapter; deterministic ingestion; exact retriever; grounded RAG orchestration; no-context fallback; evaluation CLI/query set. |

## Dataset và folder

- Nguồn chính thức: `mtue29/vietnamese-medical-dataset` trên Hugging Face; license Apache-2.0 theo dataset card.
- Full filename: `vietnamese-medical-dataset.json`; expected path `healthcare-backend/data/rag/raw/`.
- Schema thực tế được kiểm tra qua API official first-rows: JSON object với `anchor`, `positive`, `negative`, `meta.article_id`, `meta.category`, `meta.title`.
- Smoke file thực: `vietnamese-medical-dataset.subset.jsonl`, 44.868 byte, 20 raw record, 10 article duy nhất, 10 positive content duy nhất, loại 10 duplicate.
- Đây là **SUBSET INGESTION**, không phải full ingestion. Full file khoảng 1,04 GB/463.422 row không được tải mù quáng để tránh tốn tài nguyên máy phát triển.
- Đã tạo `data/rag/raw/.gitkeep` và `data/rag/processed/.gitkeep`; dataset trong hai folder bị Git ignore.

`positive` là factual corpus. `negative` không được copy vào content/metadata. `anchor` chỉ được giữ dưới `evaluation_query`; không trở thành knowledge chunk.

## Ingestion

Mọi loader trả về một `NormalizedSource` chung:

```text
JSON / CSV / PDF / DOCX
→ normalize Unicode NFC + whitespace
→ deduplicate normalized content hash
→ paragraph/heading/page-aware chunking
→ BGE-M3 batch embedding
→ existing DocumentChunk
```

- JSONL đọc theo dòng; JSON array/object-containing-array đọc streaming bằng `ijson`, không `json.load` toàn file lớn.
- CSV đọc UTF-8 theo row và tự nhận content column hỗ trợ.
- PDF dùng PyMuPDF, giữ page; scan không text trả `no_extractable_text`, không OCR.
- DOCX dùng python-docx, giữ heading/section và Unicode tiếng Việt.
- Chỉ Admin và Document `APPROVED` mới ingest. `PENDING`/`REJECTED` bị chặn.
- Path bắt buộc nằm dưới `data/rag/raw`; kiểm tra extension/type, giới hạn file configurable và SHA-256 phải khớp metadata đã được duyệt.
- Re-ingest xóa/thay chunk của đúng Document trong transaction; lỗi rollback chunk cũ và chuyển trạng thái `FAILED`, không báo thành công giả.
- CLI chạy tách khỏi Backend startup, hỗ trợ source, limit, batch size, dry-run, progress và summary không in corpus/secret.

Smoke thật: 20 raw → 10 unique → 10 duplicate removed → 10 chunk/embedding; thời gian ingestion 31,208 giây trên Windows CPU với batch size 8.

## Embedding và retrieval

- Một lazy singleton `EmbeddingService` dùng chung model `BAAI/bge-m3`; không reload model theo mỗi HTTP request.
- CPU mode chạy trực tiếp trên Windows; batch size từ settings. Runtime smoke tạo 2 vector, mỗi vector đúng 1024 dimension và norm 1,0.
- Exact retriever chỉ query Document `APPROVED` + `COMPLETED`, dùng cosine distance, threshold và Top-K configurable.
- `SET LOCAL enable_indexscan=off` giữ exact baseline; `EXPLAIN (FORMAT JSON)` xác nhận không dùng HNSW. HNSW không bị xóa và được để lại cho Phase 12.
- Source trả về chỉ gồm metadata có thật: document id, title, category, source name, article id, page.

## Gemini + RAG

Flow hiện tại:

```text
question → BGE-M3 → exact pgvector Top-K
         → approved context → existing GeminiClient → answer + sources
```

Prompt phân tách SYSTEM SAFETY, USER QUESTION và RETRIEVED CONTEXT; context bị coi là untrusted data. Không đủ context thì trả fixed no-context fallback, không gọi Gemini và không tạo citation giả. Real smoke `RagService` trả 334 ký tự và 5 source có document id thật.

MedicalRecord không có FK/import/query/embedding nào tới Document/RAG. Appointment và dữ liệu người bệnh không được dùng làm corpus. Tool Calling, AI booking, BM25, RRF, reranker, Voice, WebSocket và full Risk Alert chưa được triển khai.

## Evaluation V1

- Query set versioned: 4 `anchor` thực, ground truth là `meta.article_id` tương ứng trong official subset.
- Corpus: 10 unique positive chunk từ 20 official record.
- Model: BGE-M3; Top-K = 5; exact cosine retrieval.
- Kết quả thật: Recall@5 = 1,0000; Hit@5 = 1,0000; MRR = 0,8750; exact plan = true.

Đây là baseline smoke rất nhỏ, không chứng minh chất lượng y khoa hoặc hiệu năng ở full scale. Phase 12 mới so sánh HNSW/BM25/RRF/reranker trên corpus/query set lớn hơn.

## Database và migration

Chuỗi migration:

```text
0001_enable_pgvector
→ 0002_create_business_schema
→ 0003_phase2_invariants
→ 0004_add_json_document_type
```

Migration 0004 chỉ mở rộng CHECK `documents.file_type` thêm JSON. Không sửa 0001–0003, không tạo bảng/vector store mới. `alembic current` ở 0004 và `alembic check` không phát hiện operation mới.

## Test và kiểm chứng

Test mới bao phủ JSON schema/streaming/policy, CSV, PDF, DOCX, Unicode, malformed/no-text, chunking/hash, embedding dimension/batch/failure, governance, re-ingest, rollback, traversal/type/size guard, exact ranking/approved-only/source, no-context, provider/retrieval failure, prompt safety, frontend sources/retry và MedicalRecord hard isolation.

Real checks đã chạy:

- BGE-M3 Windows CPU: PASS, dimension 1024.
- Official subset inspection + ingestion: PASS.
- Exact pgvector plan + fixed evaluation: PASS.
- Gemini grounded RAG smoke: PASS.
- Alembic upgrade/current/check: PASS.
- Full Backend regression với PostgreSQL integration: 97/97 PASS.
- Frontend Vitest 25/25, ESLint và production build: PASS. Build chỉ cảnh báo bundle >500 kB, không chặn build.

## Issues / deferred

- Full dataset chưa tải/ingest; người vận hành phải chạy explicit full command và cân nhắc CPU/RAM/disk/time.
- Ingestion dùng transaction + deterministic replace: lỗi giữ corpus cũ và có thể chạy lại từ đầu, nhưng chưa có checkpoint tiếp tục giữa file full.
- Không OCR PDF.
- Không job queue/Redis/Celery; ingestion là CLI/API đồng bộ và deterministic.
- Không benchmark RAM, retrieval latency full-scale hoặc chất lượng lâm sàng.
- BM25/RRF/reranker/HNSW comparison thuộc Phase 12; Tool Calling thuộc Phase 9.

**PHASE 8: PASS — SMOKE/SUBSET INGESTION PASS.**
