# ENH-KB-001 — Doctor Knowledge Contribution

**Tên chức năng:** Đóng góp và kiểm duyệt tài liệu y khoa  
**Loại thay đổi:** Enhancement / Change Request sau SRS v1.1, đã hợp nhất vào SRS v1.2  
**Ngày audit:** 17/11/2026  
**Trạng thái:** IMPLEMENTED / VERIFIED / DOCUMENTED — CLOSED  
**Phạm vi:** Audit, decision lock, schema 0005, secure Doctor upload Backend, Doctor/Admin UI, full Doctor → Admin → ingest → retrieval verification và SRS v1.2/traceability sync; không phải Phase 15.

### KB-001D documentation closure — 18/11/2026

- SRS v1.2 được tạo bằng cách kế thừa nguyên baseline v1.1 và bổ sung ENH-KB-001 sau verification; đề cương và lịch sử Phase 1–14 không bị viết lại.
- FR-DOCS-07..12, BR-25..30, NFR-DOCS-SEC-01/02, NFR-DOCS-PRIV-01, NFR-DOCS-AUD-01, AC-DOCS-09..13 và DR-11 đã được hợp nhất và truy vết.
- Current final evidence: Backend 191 passed; Frontend 54 passed; targeted Frontend 8 passed; targeted contribution/download 19 passed; contribution + RAG 25 passed; Playwright 5/5; Alembic `0005_document_contribution` exactly one head/no drift; ESLint/build/compileall/pip check PASS.
- KB-001D chỉ đồng bộ tài liệu và tái sử dụng evidence KB-001B/001C; không sửa implementation, không tạo migration và không chạy lại test.

### KB-001A.1 decision lock

Các quyết định trong mục này là source of truth cho KB-001B:

- Giữ nguyên tên vật lý `approved_by` và `approved_at`; không rename và không tạo `reviewed_by/reviewed_at` song song.
- `approved_by` mang nghĩa người thực hiện review cuối cùng, gồm APPROVE hoặc REJECT; `approved_at` là thời điểm review cuối cùng.
- `rejection_reason` nullable trong DB; bắt buộc có nội dung khi REJECT, luôn `NULL` khi APPROVE và được clear khi Doctor resubmit.
- `author_name`, `organization`, `publication_year` đều optional/nullable.
- DB chỉ dùng constraint năm ổn định: `publication_year IS NULL OR publication_year >= 1800`; upper bound `current_year + 1` được kiểm tra tại Pydantic/application.
- `mime_type` và `file_size_bytes` nullable cho legacy; upload mới bắt buộc Backend xác minh/lưu và size phải lớn hơn 0.
- Tại thời điểm Decision Lock, unique checksum được defer tới data audit KB-001B. Audit sau đó đã sạch và migration 0005 đã triển khai `UNIQUE(checksum_sha256)` như ghi trong implementation record.
- Storage, RBAC, RAG boundary và MedicalRecord isolation được khóa như mô tả trong tài liệu này.

### KB-001B implementation record — 18/11/2026

KB-001B đã triển khai schema và secure Doctor upload trên chính Document module hiện hữu. Không tạo corpus, vector store, ingestion service hoặc module thứ hai.

### KB-001C implementation and verification record — 18/11/2026

KB-001C đã hoàn thiện workflow trên UI bằng cách mở rộng đúng Document module/page hiện hữu. Không tạo corpus, vector store, ingestion pipeline hay Admin Document page thứ hai; không tạo migration 0006.

#### Doctor UI

- Thêm route/menu chỉ dành cho Doctor: `Tài liệu đóng góp` (`/doctor/contributions`). Patient/Staff không thấy menu và route vẫn được RoleRoute bảo vệ.
- Doctor xem danh sách contribution của chính mình với title, original filename/type, provenance, ngày gửi, trạng thái thân thiện và rejection reason; không hiển thị storage key, checksum, internal UUID hoặc raw enum.
- Dialog upload hỗ trợ PDF/DOCX/CSV/JSON/JSONL, preliminary validation 25 MB, loading/disabled state và thông báo lỗi thân thiện; owner/checksum/MIME/size/status vẫn do Backend quyết định.
- Doctor được sửa metadata PENDING hoặc REJECTED và resubmit; trạng thái sau resubmit là `PENDING + NOT_INGESTED`. Doctor không có action approve/reject/ingest.

#### Admin review, file inspection and ingestion UI

- Mở rộng current Admin Document page để hiển thị uploader, provenance, review/ingestion status và rejection reason.
- Admin có thể tải file gốc để kiểm tra qua endpoint tối thiểu `GET /api/v1/documents/{document_id}/file`; endpoint chỉ cho ADMIN, resolve relative storage key trong `data/rag/raw`, trả 404 an toàn nếu file thiếu/path thoát root và không lộ absolute path.
- APPROVE và REJECT vẫn là review riêng; REJECT bắt buộc reason, APPROVE clear reason. TanStack Query invalidation/refetch được thực hiện sau upload, edit/resubmit, approve, reject và ingest.
- Ingest không tự chạy khi approve. Nút `Đưa vào kho tri thức` chỉ xuất hiện cho `APPROVED + NOT_INGESTED/FAILED`; response thật quyết định `COMPLETED/FAILED` và UI không giả lập thành công.
- Quan hệ hiển thị uploader dùng `selectin`, tránh outer join làm hỏng câu `SELECT ... FOR UPDATE` của ingestion trên PostgreSQL.

#### Golden Path and RAG evidence

Playwright đã chạy với Backend + PostgreSQL thật, cookie/JWT thật và DEV auth tắt:

```text
Admin tạo Doctor account/profile qua Dialog
→ Doctor login và upload JSON synthetic qua UI
→ PENDING + NOT_INGESTED
→ Admin tải file và REJECT kèm reason
→ Doctor thấy reason, sửa metadata và resubmit
→ Admin APPROVE
→ retrieval assertion: document chưa xuất hiện
→ Admin Ingest bằng BGE-M3 thật
→ COMPLETED + document_chunks được tạo
→ ExactDenseRetriever lấy đúng marker, document_id/title/source traceability
→ Patient/Staff không có corpus management permission
```

Không gọi live Gemini để làm điều kiện PASS. Tài liệu kiểm thử là synthetic, không có dữ liệu bệnh nhân. MedicalRecord isolation và filter `APPROVED + COMPLETED` được giữ nguyên.

#### KB-001C verification evidence

- Backend contribution/download targeted với PostgreSQL thật: **19 passed**.
- Backend contribution + RAG integration targeted: **25 passed**.
- Full Backend với PostgreSQL integration: **191 passed**.
- Frontend KB-001C targeted: **8 passed**; full Frontend: **54 passed**.
- ESLint: PASS; production build: PASS; Python `compileall`: PASS; `pip check`: PASS.
- KB-001C Playwright Golden Path: **1 passed**.
- Existing business workflow và release readiness Playwright: PASS sau khi đồng bộ hai stale UI-label assertions.
- Alembic current/head: `0005_document_contribution (head)`, exactly one head; `alembic check`: no new upgrade operations.

#### File replacement decision and remaining limitations

**FILE REPLACEMENT: DEFERRED.** Doctor có thể tạo contribution mới thay vì thay trusted file. PENDING/REJECTED chỉ hỗ trợ metadata edit/resubmit; APPROVED/COMPLETED không cho thay file/content trực tiếp. Không tạo versioning table.

Các giới hạn còn lại: upload tối đa 25 MB; không OCR/image/XLSX/PPTX/TXT; ingestion synchronous; storage local cần persistent disk khi deploy; lần tải model có thể hiện HF unauthenticated warning nếu chưa cấu hình optional `HF_TOKEN`. Các giới hạn này không chặn Golden Path KB-001C.

#### PostgreSQL data audit trước migration

| Kiểm tra | Kết quả |
|---|---:|
| Tổng `documents` | 2 |
| Checksum NULL | 0 |
| Checksum rỗng | 0 |
| Checksum không đúng 64 ký tự lowercase hex | 0 |
| Duplicate checksum | 0 |
| Cùng checksum nhưng nhiều `version_number` | 0 |
| `APPROVED + COMPLETED` | 2 |

Hai record là các controlled dataset subset đã dùng cho Phase 8/12; đều version 1, checksum khác nhau và `APPROVED + COMPLETED`. Không có dữ liệu nào bị xóa/merge/sửa trong audit.

Kết luận checksum: dữ liệu thật cho phép thay unique `(checksum_sha256, version_number)` bằng `UNIQUE(checksum_sha256)`. Application vẫn query trước và trả `409 document_content_exists`; unique DB là guard cuối cho race condition. Response duplicate không trả title, owner, checksum đầy đủ hay storage path.

#### Migration và actual schema

- Revision: `0005_document_contribution`, nối trực tiếp `0004_add_json_document_type`.
- Added nullable legacy-compatible columns: `rejection_reason`, `mime_type`, `file_size_bytes`, `author_name`, `organization`, `publication_year`.
- Stable constraints: `file_size_bytes IS NULL OR file_size_bytes > 0`; `publication_year IS NULL OR publication_year >= 1800`.
- Dynamic upper year `current_year + 1` được enforce tại Pydantic/application.
- Giữ tên vật lý `approved_by/approved_at` và thêm DB/model comment về semantics latest reviewer.
- Một Alembic head duy nhất; `alembic check` không phát hiện drift.

#### Actual Backend API

```text
POST  /api/v1/documents/contributions
GET   /api/v1/documents/contributions/me
GET   /api/v1/documents/contributions/{document_id}
PATCH /api/v1/documents/contributions/{document_id}
```

`POST` nhận multipart `file`, `title` và provenance optional. Backend tự sinh/xác minh owner, statuses, checksum, MIME, size, original filename và relative storage key. Internal `storage_key` và full checksum không nằm trong Doctor-safe response.

DOCTOR được upload/list/get own/edit-resubmit PENDING hoặc REJECTED. ADMIN được phép dùng contribution endpoint và giữ quyền review/ingest hiện có. STAFF/PATIENT không nhận quyền contribution. Resubmit REJECTED clear `approved_by`, `approved_at`, `rejection_reason` và quay về `PENDING + NOT_INGESTED` trong cùng transaction. File replacement chưa được triển khai trong KB-001B.

#### Storage and validation implementation

- Settings: `DOCUMENT_UPLOAD_ROOT=data/rag/raw/uploads`, `DOCUMENT_UPLOAD_MAX_BYTES=25000000`.
- Root resolve từ `BACKEND_ROOT`, bắt buộc nằm trong `data/rag/raw`; DB chỉ lưu relative POSIX key.
- Stream 1 MiB blocks vào temp cùng filesystem, enforce hard size limit và tính SHA-256 trong một lượt.
- Final name là UUID + validated extension; finalize dùng atomic no-overwrite link và cleanup idempotent.
- Supported: PDF, DOCX, CSV, JSON và JSONL mapped về `file_type=JSON`.
- Content validation reuse loader hiện tại: PDF signature/parse, DOCX ZIP members/parse, CSV UTF-8/content column, JSON/JSONL UTF-8/stream parse.
- Upload chỉ tạo `PENDING + NOT_INGESTED`; không approve, ingest, embed hoặc gọi RAG tự động.

#### Verification evidence

- KB-001B + Document/RAG/security targeted: **46 passed**.
- Full Backend với PostgreSQL integration: **190 passed**.
- `compileall`: PASS.
- `pip check`: `No broken requirements found`.
- Alembic current/heads: `0005_document_contribution (head)`; exactly one head.
- Alembic check: `No new upgrade operations detected`.
- Frontend tests không chạy vì KB-001B không sửa Frontend.

#### Historical remaining work immediately after KB-001B

- Tại thời điểm vừa hoàn tất KB-001B, Doctor Frontend contribution page/form chưa được triển khai. KB-001C hiện đã hoàn thành phần này.
- Tại thời điểm đó, Admin Document UI chưa hỗ trợ đầy đủ rejection reason, review file và nút ingest/re-ingest. KB-001C hiện đã mở rộng page hiện hữu.
- Tại thời điểm đó, full Doctor → Admin → ingest → RAG E2E chưa chạy. KB-001C hiện đã chạy Golden Path và retrieval/source assertion thành công.
- Actual file replacement cho contribution đã APPROVED/COMPLETED vẫn deferred; chỉ metadata edit/resubmit PENDING/REJECTED đã có.
- KB-001C nay đã IMPLEMENTED/VERIFIED; bước tiếp theo riêng biệt là KB-001D documentation sync.

## 1. Historical motivation before KB-001B

Trước KB-001B, nguồn tri thức chỉ được Staff/Admin đăng ký bằng metadata và đường dẫn file đã có trên máy chủ. Bác sĩ chưa có luồng đóng góp tài liệu. Cách làm cũ buộc người vận hành phải tự chép file, tự tính SHA-256 và nhập `storage_key`, không phù hợp khi hệ thống đã triển khai.

ENH-KB-001 được tạo để cho phép Doctor đóng góp tài liệu y khoa vào đúng corpus hiện hữu, nhưng tài liệu chỉ được dùng bởi RAG sau khi Admin kiểm duyệt và ingestion hoàn tất. Backend foundation đã hoàn thành ở KB-001B; UI và full E2E đã hoàn thành ở KB-001C.

## 2. Historical problem before KB-001B

Các bullet dưới đây là baseline tại thời điểm audit ENH-KB-001A, không phải trạng thái Backend hiện tại:

- Backend chưa có multipart upload endpoint; `POST /documents` chỉ đăng ký metadata.
- `DocumentService` chỉ cho `STAFF`/`ADMIN` list, get và create; Doctor chưa có quyền đóng góp/xem tài liệu của mình.
- Admin UI yêu cầu nhập tên file, `storage_key` và SHA-256 thủ công; UI chưa upload bytes, chưa có nút ingest và chưa hỗ trợ JSON.
- Review đã có APPROVE/REJECT nhưng chưa lưu lý do từ chối.
- Chưa lưu MIME type, kích thước file, tác giả, tổ chức và năm xuất bản.
- Thư mục RAG runtime đã được Git ignore, nhưng root upload chưa cấu hình qua Settings và ingestion đang cố định trong `data/rag/raw`.
- Unique hiện tại là `(checksum_sha256, version_number)`, vì vậy cùng một file có thể được đăng ký lại nếu đổi version.

## 3. Architecture reuse

Không tạo corpus, vector store, ingestion service hoặc module tài liệu thứ hai. Luồng mục tiêu tái sử dụng nguyên trạng kiến trúc sau:

```text
Doctor upload
  → existing documents (PENDING)
  → Admin APPROVE / REJECT
  → existing DocumentIngestionService
  → existing loaders (JSON/CSV/PDF/DOCX)
  → existing normalize/dedup/chunk
  → existing BGE-M3 EmbeddingService
  → existing document_chunks VECTOR(1024)
  → existing PostgreSQL + pgvector
  → existing RAGService/retrievers
```

RAG hiện đã lọc đồng thời:

```text
documents.approval_status = APPROVED
AND documents.ingestion_status = COMPLETED
```

Vì vậy `APPROVED` không đồng nghĩa với đã embedded và không cần thay đổi điều kiện retrieval.

## 4. Historical schema audit before KB-001B

Bảng này giữ nguyên evidence audit trước migration 0005. Actual schema sau KB-001B được ghi tại **KB-001B implementation record** ở đầu tài liệu.

| FIELD | EXISTS | CURRENT PURPOSE | REUSABLE | MISSING FOR ENH-KB-001 | RECOMMENDATION |
|---|---|---|---|---|---|
| `id` | Yes | UUID primary key từ mixin | Yes | No | Giữ nguyên |
| `title` | Yes | Tiêu đề tài liệu | Yes | No | Giữ nguyên |
| document type | Yes, tên `file_type` | `JSON/CSV/PDF/DOCX` | Yes | No | Giữ tên hiện tại; không thêm enum mới |
| review status | Yes, tên `approval_status` | `PENDING/APPROVED/REJECTED` | Yes | No | Reuse `PENDING`; không đổi thành `PENDING_REVIEW` chỉ để khớp wording |
| ingestion status | Yes, `ingestion_status` | `NOT_INGESTED/PROCESSING/COMPLETED/FAILED` | Yes | No | Giữ nguyên |
| `uploaded_by` | Yes | FK người đăng ký/upload | Yes | No | Dùng làm owner contribution |
| `created_by` | No | Không có field riêng | Yes via `uploaded_by` | No | Không thêm field trùng nghĩa |
| reviewed by | Yes, tên vật lý `approved_by` | Người thực hiện review cuối cùng, gồm APPROVE hoặc REJECT | Yes | No | **KEEP**; không rename và không thêm `reviewed_by` song song |
| reviewed at | Yes, tên vật lý `approved_at` | Thời điểm review cuối cùng, gồm APPROVE hoặc REJECT | Yes | No | **KEEP**; không rename và không thêm `reviewed_at` song song |
| `rejection_reason` | No | Chưa lưu lý do reject | No | **Yes** | Thêm nullable text/string; application bắt buộc khi REJECTED |
| source | Yes, `source_name` | Tên nguồn/provenance | Yes | No | Giữ nguyên |
| author | No | Chưa lưu tác giả | No | Yes for provenance | Thêm nullable `author_name` |
| organization | No | Chưa lưu tổ chức phát hành | No | Yes for provenance | Thêm nullable `organization` |
| `source_url` | Yes | URL nguồn | Yes | No | Giữ nguyên |
| publication year | No | Chưa lưu năm xuất bản | No | Yes for provenance | Thêm nullable; DB CHECK chỉ `IS NULL OR >= 1800`; upper bound động ở application |
| original filename | Partly, tên `file_name` | Tên file do client khai báo; hiện chưa có upload | Yes | No | Chuẩn hóa nghĩa là original filename; không dùng làm tên lưu trữ |
| stored filename/path | Yes, `storage_key` | Đường dẫn/key nội bộ tới file | Yes | No | Lưu relative key sinh bởi server |
| MIME type | No | Chưa lưu content type đã xác minh | No | **Yes** | Thêm nullable để tương thích dữ liệu cũ; bắt buộc với upload mới |
| file size | No | Chưa lưu byte count | No | **Yes** | Thêm nullable `file_size_bytes`; CHECK `> 0`; bắt buộc với upload mới |
| SHA-256 | Yes, `checksum_sha256` | Kiểm tra bytes trước ingestion; tham gia unique hiện tại | Yes | Duplicate policy chưa đủ | Giữ field; siết duplicate policy |
| timestamps | Yes | `created_at`, `updated_at` từ mixin | Yes | No | Giữ nguyên |
| ingestion metadata | Partly | `ingestion_error`; counts/duration chỉ trả trong response/audit log | Yes for current scope | Không bắt buộc thêm | Giữ status/error và AuditLog; chưa thêm JSON metadata khi chưa có nhu cầu báo cáo rõ |
| chunks | Yes | Quan hệ 1:N tới `document_chunks`; cascade/re-ingest | Yes | No | Giữ nguyên |

### `document_chunks` hiện tại

Schema đã có `document_id` FK cascade, `chunk_index`, `content`, `embedding VECTOR(1024)`, `page_number`, `section`, `metadata JSONB`, `content_hash`, `created_at`, unique `(document_id, chunk_index)` và HNSW cosine index. Không cần thay đổi cho Doctor contribution.

## 5. Migration decision

**MIGRATION REQUIRED: YES — IMPLEMENTED AS `0005_document_contribution`.**

Không tạo bảng mới. Một revision Alembic nối tiếp `0004_add_json_document_type` được đề xuất ở bước implementation, sau khi xác nhận contract cuối cùng. Migration tối thiểu:

1. Thêm `rejection_reason` nullable để lưu lý do Admin từ chối; dữ liệu cũ giữ `NULL`. APPROVE luôn clear reason; REJECT bắt buộc reason; resubmit clear reason cùng reviewer/time.
2. Thêm `mime_type` nullable và `file_size_bytes` nullable để tương thích bản ghi cũ; API upload mới bắt buộc có giá trị do server xác minh. Thêm CHECK `file_size_bytes IS NULL OR file_size_bytes > 0`.
3. Thêm metadata provenance nullable: `author_name`, `organization`, `publication_year`. DB CHECK của năm chỉ ổn định: `publication_year IS NULL OR publication_year >= 1800`; upper bound `publication_year <= current_year + 1` được enforce tại Pydantic/application, không hard-code thời gian động trong migration.
4. Giữ nguyên `approved_by/approved_at` với semantics reviewer cuối cùng; không rename và không thêm cột song song.
5. Data audit KB-001B không phát hiện checksum NULL/invalid/duplicate hoặc multi-version duplicate. Migration 0005 đã thay unique `(checksum_sha256, version_number)` bằng `UNIQUE(checksum_sha256)` mà không sửa/xóa hai record hợp lệ.

`file_name` được reuse làm original filename và `storage_key` làm internal storage key, nên không thêm cột trùng nghĩa.

## 6. Review and ingestion lifecycle

### Review lifecycle

```text
PENDING → APPROVED
PENDING → REJECTED
REJECTED → PENDING (Doctor sửa và resubmit)
```

- Doctor không được approve/reject.
- APPROVE đặt `rejection_reason = NULL`.
- REJECT bắt buộc có `rejection_reason` hợp lệ.
- Resubmit xóa `approved_by`, `approved_at`, `rejection_reason` và quay về `PENDING` trong cùng transaction.
- `APPROVED` không được sửa file/metadata nguồn theo cách giữ nguyên trust.
- Nếu sau này cho replace tài liệu đã approved/completed, replacement phải xóa chunks liên quan hoặc tạo revision nghiệp vụ rõ, reset `approval_status=PENDING`, `ingestion_status=NOT_INGESTED`, reviewer/time/reason và yêu cầu review lại. ENH-KB-001A chưa thiết kế versioning table.

### Ingestion lifecycle

```text
NOT_INGESTED → PROCESSING → COMPLETED
                         ↘ FAILED
```

- Chỉ Admin được gọi ingest/re-ingest.
- Chỉ Document `APPROVED` đủ điều kiện ingest.
- `REJECTED` không ingest và không retrieval.
- Existing ingestion rollback giữ chunks cũ nếu re-ingest lỗi, ghi `FAILED`, và retrieval loại tài liệu vì không còn `COMPLETED`.

## 7. Runtime storage implementation

Reuse cây runtime hiện có thay vì tạo storage độc lập:

```text
healthcare-backend/
└── data/
    └── rag/
        └── raw/
            └── uploads/
                └── <uuid>.<validated-extension>
```

Settings/env đã triển khai:

```text
DOCUMENT_UPLOAD_ROOT=data/rag/raw/uploads
DOCUMENT_UPLOAD_MAX_BYTES=25000000
```

- Default được resolve từ `BACKEND_ROOT`, không từ current working directory.
- Config không chấp nhận root nằm ngoài `data/rag/raw` trừ khi ingestion path policy được thay đổi có kiểm soát.
- `storage_key` lưu relative POSIX-style key, ví dụ `data/rag/raw/uploads/8f...c2.pdf`; không lưu absolute Windows path.
- Cây `data/rag/raw/*` hiện đã được `.gitignore`; thêm tài liệu không cần rebuild/redeploy source code, nhưng môi trường deploy phải dùng persistent volume/disk phù hợp.
- Không lưu upload trong `app/`, `src/`, `public/` hoặc Git.

Giới hạn web upload mặc định 25 MB đã được triển khai để an toàn/dễ demo, tách khỏi `RAG_MAX_FILE_BYTES=2 GB` vốn phục vụ controlled ingestion/dataset. Có thể điều chỉnh bằng env sau đánh giá vận hành; Doctor upload không mặc định nhận file 2 GB qua HTTP.

## 8. Safe naming and file validation implementation

### Safe filename

- Chỉ giữ basename gốc sau normalize để hiển thị trong `file_name`.
- Tên lưu trữ do server sinh: `uuid4 + extension đã xác minh`.
- Không nối trực tiếp filename client vào path.
- Resolve path và xác nhận `is_relative_to(DOCUMENT_UPLOAD_ROOT)` trước mọi write/read/delete.
- Tạo file mới theo chế độ không overwrite; UUID collision trả lỗi và sinh lại.

### Validation order

1. Chỉ nhận multipart field duy nhất, reject file rỗng.
2. Streaming với hard byte limit; không đọc file lớn toàn bộ vào RAM.
3. Extension allowlist: `.pdf`, `.docx`, `.csv`, `.json` (có thể `.jsonl` nếu contract công khai rõ là `JSON`).
4. Declared MIME chỉ là tín hiệu, không phải nguồn tin duy nhất.
5. Kiểm tra content:
   - PDF: magic `%PDF-` và mở được bằng loader hiện tại.
   - DOCX: ZIP hợp lệ, có `[Content_Types].xml` và `word/document.xml`.
   - CSV: UTF-8, có header và content column được loader hỗ trợ.
   - JSON/JSONL: UTF-8 và streaming parser/loader hiện tại đọc được schema hỗ trợ.
6. Tính SHA-256 trên bytes đã ghi trong cùng lượt stream.
7. Ghi `mime_type`, `file_size_bytes`, checksum và generated storage key từ server; không nhận các giá trị này từ client như dữ liệu authoritative.

Không hỗ trợ XLSX, PPTX, TXT, ảnh/OCR hoặc ZIP thường trong enhancement này.

## 9. SHA-256 and duplicate policy

Trước KB-001B, ingestion đã tính lại SHA-256 trước khi tạo chunk và chunking đã dedup content trong từng document, nhưng hai cơ chế đó chưa đủ chống duplicate upload. KB-001B đã bổ sung application duplicate query, safe `409` và `UNIQUE(checksum_sha256)` làm DB guard cuối.

Target business policy:

- Trước insert, query `documents.checksum_sha256` trên checksum chuẩn lowercase.
- Nếu đã có bản ghi, trả `409 document_content_exists` kèm document id/status phù hợp với quyền người gọi; không tạo document/chunks mới.
- Data audit KB-001B đã kiểm tra checksum NULL, invalid, duplicate, multi-version và trạng thái hai controlled dataset record; không phát hiện xung đột.
- `UNIQUE(checksum_sha256)` hiện là DB guard cuối chống hai upload đồng thời; application query vẫn trả thông báo an toàn, dễ hiểu.
- Cùng bytes nhưng đổi title/version/filename vẫn là duplicate. Phiên bản mới chỉ hợp lệ khi bytes/checksum thay đổi.
- Không dựa vào chunk dedup để hợp thức hóa duplicate upload.

## 10. Authorization matrix

| Action | DOCTOR | ADMIN | STAFF | PATIENT |
|---|---:|---:|---:|---:|
| Upload contribution | Own only | Allowed under current management policy | Existing metadata permission unchanged; no new upload workflow permission | No |
| List/get contribution | Own only | All | Existing current permission only | No |
| Edit metadata/file | Own `PENDING`; own `REJECTED` then resubmit | Review/management policy | No new permission | No |
| See rejection reason | Own only | All | No new permission | No |
| Approve/reject | No | Yes | No | No |
| Ingest/re-ingest | No | Yes | No | No |
| Change owner | No | No through normal update | No | No |
| View another Doctor's private contribution | No | Yes for review | No new permission | No |

Backend remains authoritative. Contribution routes hiện truyền existing `ActorContext` vào existing `DocumentService`; Doctor own list/get và object ownership đã được triển khai mà không tạo `DoctorDocumentService` thứ hai. Admin pending/review/ingest UI đã hoàn thành ở KB-001C trên current Document page.

## 11. MedicalRecord hard isolation

Source audit confirms current Document/RAG code does not import/query MedicalRecord. Existing test `test_medical_record_is_hard_isolated_from_rag_source` enforces this boundary.

Invariant remains mandatory:

```text
MedicalRecord NEVER → Document → DocumentChunk → embedding → RAG → Gemini
```

- Upload API chỉ nhận file tri thức y khoa và metadata provenance.
- Không có helper/API “export MedicalRecord to Document”.
- Không đọc appointment, patient history, lab result hoặc clinical file để tạo corpus.
- Audit log không chứa nội dung file hay dữ liệu lâm sàng.
- Dữ liệu thật có thông tin định danh/người bệnh phải bị từ chối theo policy vận hành; đồ án tiếp tục dùng dữ liệu demo/synthetic hoặc nguồn công khai đã kiểm duyệt.

## 12. Transaction and failure behavior

| Failure | Required behavior |
|---|---|
| File validation/write fails | Không insert Document; xóa temp file |
| File write succeeds, DB transaction fails | Rollback DB và xóa temp/final file do request đó tạo |
| DB metadata inserted but final move fails | Rollback transaction; xóa temp; không để Document trỏ tới file thiếu |
| Duplicate checksum | Trả 409; xóa temp; không tạo record/chunks |
| Unsupported/empty/oversized file | Trả 400/413/422 phù hợp; không tạo record/file lâu dài |
| Approve succeeds, ingestion later fails | Document giữ `APPROVED`, ingestion chuyển `FAILED`, lưu lỗi an toàn; không retrieval; Admin có thể retry |
| First ingestion fails midway | Rollback partial chunks; trạng thái `FAILED`; không coi là COMPLETED |
| Re-ingestion fails | Existing transaction giữ chunks cũ nhưng status `FAILED`; không retrieval cho tới lần ingest thành công tiếp theo |

File/DB không có distributed transaction. KB-001B hiện stream vào file tạm cùng filesystem, validate/hash, tạo metadata trong transaction, atomic no-overwrite finalize rồi commit; exception thực hiện rollback và cleanup idempotent cho temp/final file của request. Không thêm Redis/Celery. Cleanup job/startup orphan audit chưa cần triển khai trong phạm vi hiện tại.

## 13. Existing code reused by KB-001B

- `Document`, `DocumentChunk` SQLAlchemy models và FK/index/pgvector hiện có.
- `DocumentRepository` và `DocumentService` hiện có; mở rộng thay vì tạo module mới.
- Existing review endpoint/service và `AuditLog`.
- `DocumentIngestionService`, checksum verification, path boundary, size guard, rollback/re-ingest behavior.
- Loaders JSON/CSV/PDF/DOCX, normalization, dedup, chunking.
- Existing BGE-M3 embedding adapter.
- Dense/HNSW/BM25/RRF/reranker retrieval trên cùng `document_chunks`.
- `RagService` và điều kiện `APPROVED + COMPLETED`.
- Existing Auth/JWT/RBAC/ActorContext.
- Current Admin Document UI đã được mở rộng ở KB-001C; không tạo trang quản trị song song.

## 14. Acceptance boundaries for ENH-KB-001A

### Historical scope of KB-001A foundation

- Audit source/schema/pipeline/RBAC/storage/failure behavior.
- Chốt migration requirement và contract đề xuất.
- Chốt runtime storage, naming, validation và duplicate policy.
- Chuẩn bị requirement SRS v1.2 và implementation stages.

### Explicitly out of scope for KB-001A foundation

- Không tạo migration/code/API/UI trong foundation task này.
- Không build Doctor contribution page, Admin review page hay full upload dialog.
- Không chạy full Doctor/Admin E2E.
- Không sửa SRS v1.1, đề cương hoặc lịch sử Phase 1–14.
- Không tạo Phase 15, corpus/vector store/pipeline thứ hai.

## 15. Requirements merged into SRS v1.2

SRS v1.2 kế thừa toàn bộ SRS v1.1. Các identifier đã được kiểm tra không trùng và hợp nhất chính thức như dưới đây.

### Functional requirements

- **FR-DOCS-07:** Doctor được upload một tài liệu tri thức y khoa ở các định dạng PDF/DOCX/CSV/JSON/JSONL tương thích JSON cùng metadata provenance; owner lấy từ ActorContext.
- **FR-DOCS-08:** Hệ thống lưu original filename, generated storage key, verified MIME, byte size và SHA-256; file runtime không nằm trong source control.
- **FR-DOCS-09:** Doctor chỉ list/get contribution của mình; được sửa/resubmit khi PENDING hoặc REJECTED theo policy; không được approve/reject/ingest.
- **FR-DOCS-10:** Admin được xem pending contribution, approve hoặc reject; reject bắt buộc reason và review phải audit được.
- **FR-DOCS-11:** Chỉ APPROVED document được Admin ingest/re-ingest qua pipeline hiện có; RAG chỉ dùng APPROVED + COMPLETED.
- **FR-DOCS-12:** Duplicate upload theo SHA-256 bị từ chối rõ ràng; không được chỉ dựa vào chunk dedup.

### Business rules

- **BR-25:** Owner lấy từ ActorContext/JWT, không nhận UUID owner từ client và không được thay đổi qua update thông thường.
- **BR-26:** Doctor chỉ quản lý own contribution; Admin review/ingest; Staff và Patient không nhận quyền corpus-management mới.
- **BR-27:** Review và ingestion là hai lifecycle độc lập; chỉ `APPROVED + COMPLETED` được retrieval.
- **BR-28:** Cùng SHA-256 là duplicate content dù title, filename hoặc version khác nhau.
- **BR-29:** File APPROVED/COMPLETED không được thay âm thầm; replacement/versioning deferred, nội dung mới tạo contribution mới.
- **BR-30:** REJECT bắt buộc reason; resubmit clear review metadata và reset về `PENDING + NOT_INGESTED`.

### Security/privacy/non-functional requirements

- **NFR-DOCS-SEC-01:** Server enforce path containment, generated filename, allowlist, content validation, streaming size limit và checksum.
- **NFR-DOCS-SEC-02:** File/metadata operations có transaction compensation; không để orphan record/file hoặc partial chunks được đánh dấu COMPLETED.
- **NFR-DOCS-PRIV-01:** MedicalRecord và mọi dữ liệu người bệnh không được chuyển thành Document, chunk, embedding, RAG context hoặc Gemini context.
- **NFR-DOCS-AUD-01:** Upload/resubmit/review/ingest được audit bằng metadata an toàn, không ghi nội dung tài liệu hoặc secret.

### Acceptance criteria

- **AC-DOCS-09:** Doctor upload file hợp lệ tạo một Document `PENDING/NOT_INGESTED` và chỉ thấy contribution của mình.
- **AC-DOCS-10:** Duplicate, path traversal, unsupported, empty và oversized upload bị từ chối mà không để orphan.
- **AC-DOCS-11:** Doctor không approve/reject/ingest; Admin reject lưu reason; Admin approve chưa làm tài liệu xuất hiện trong RAG cho tới khi ingestion `COMPLETED`.
- **AC-DOCS-12:** Ingestion thành công tạo chunks trong store hiện có; RAG có source traceability và không chứa MedicalRecord.
- **AC-DOCS-13:** Thay file trusted buộc review lại; failure/re-ingest không tạo partial corpus được coi là hợp lệ.

## 16. Implementation stages

1. **Schema + contract (KB-001B — DONE):** giữ `approved_by/approved_at`, audit checksum, migration 0005, model/schema và unique checksum guard.
2. **Storage foundation (KB-001B — DONE):** Settings/env, upload root resolver, streaming temp file, content validation, SHA-256 và compensation cleanup.
3. **Backend contribution workflow (KB-001B — DONE):** upload, Doctor own list/get, metadata edit/resubmit, RBAC/object ownership và audit event trên existing module.
4. **Targeted security/tests (KB-001B — DONE):** filename/path, formats/content, size/empty, duplicate DB guard, RBAC, lifecycle, failure cleanup, RAG/MedicalRecord isolation.
5. **Minimal UI (KB-001C — DONE):** Doctor contribution form/list/status/reason; mở rộng current Admin page cho review/download-safe preview/ingest; không tạo module song song.
6. **E2E (KB-001C — DONE):** Doctor → Admin → ingest → RAG source traceability và role-boundary evidence.
7. **SRS v1.2 + traceability sync (KB-001D — DONE):** SRS, requirement traceability, final matrices/report materials và Change Request đã đồng bộ; historical Phase evidence được giữ nguyên.

## 17. Closure

KB-001D đã hoàn thành và ENH-KB-001 được đóng. Không tạo KB-001E hoặc Phase 15. Các giới hạn hiện tại được chấp nhận: **FILE REPLACEMENT DEFERRED**, upload mặc định 25 MB, local storage cần persistent disk khi deploy, ingestion synchronous, không OCR/image/XLSX/PPTX/TXT/antivirus scanning và có thể xuất hiện optional HF_TOKEN warning.

---

## Final decision

- **MIGRATION:** `0005_document_contribution` APPLIED
- **REVIEWER PHYSICAL FIELDS:** KEEP `approved_by/approved_at`
- **CHECKSUM CONSTRAINT:** `UNIQUE(checksum_sha256)` AFTER CLEAN DATA AUDIT
- **SECOND TABLE/CORPUS/PIPELINE:** NO
- **CURRENT RAG FILTER:** REUSE (`APPROVED + COMPLETED`)
- **KB-001B SCHEMA + SECURE DOCTOR UPLOAD:** **PASS — READY FOR KB-001C**
- **KB-001C DOCTOR UI + ADMIN REVIEW/INGEST:** **PASS**
- **KB-001D SRS v1.2 + TRACEABILITY SYNC:** **PASS**
- **FINAL ENHANCEMENT STATUS:** **IMPLEMENTED / VERIFIED / DOCUMENTED — CLOSED**
- **FILE REPLACEMENT:** **DEFERRED / OUT OF CURRENT SCOPE**
