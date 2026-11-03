# Healthcare Backend

Python 3.12 + FastAPI, REST API, Modular Monolith. Phase 3-6 hoàn thiện Business MVP; Phase 7-10 hoàn thiện AI MVP; Phase 11 thêm Vietnamese push-to-talk STT và Handoff WebSocket trên các service hiện có; Phase 12 hoàn thiện retrieval experiments; Phase 13 harden security, dependency, error handling, rate limit và release regression. Business MVP vẫn không phụ thuộc AI/Voice/WebSocket.

## Setup

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Nếu launcher `py -3.12` không nhận Python do uv quản lý:

```powershell
$python312 = uv python find 3.12
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -PythonPath $python312
```

Script giữ nguyên `.env` và `.venv` đã có; không cần kích hoạt venv hoặc thay ExecutionPolicy toàn hệ thống. Dependency trực tiếp khai báo ở `requirements.txt`; bản tái lập đầy đủ sau kiểm thử nằm ở `requirements.lock.txt`.

## PostgreSQL và pgvector trên Windows

Máy phát triển đã có PostgreSQL 18.6 x64 tại `C:\Program Files\PostgreSQL\18`, Windows Service `postgresql-x64-18` đang chạy ở cổng 5432. Không dùng tài khoản `postgres` để chạy ứng dụng.

Phân biệt: package Python `pgvector` không cài extension trên PostgreSQL server. Server cần `vector.dll`, `vector.control` và các SQL extension files đúng major version/kiến trúc. Theo [hướng dẫn Windows chính thức của pgvector](https://github.com/pgvector/pgvector#windows), build bằng Microsoft C++ x64 native tools và `nmake`; script đang pin source tag `v0.8.7`, có hỗ trợ PostgreSQL 13+.

Nếu chưa có Microsoft C++ Build Tools, mở PowerShell **Run as Administrator** rồi chạy:

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

Sau khi cài xong, trong PowerShell Administrator tại thư mục backend:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_pgvector.ps1
```

Script kiểm tra PostgreSQL x64, dùng source chính thức, không ghi đè extension đã có. Chỉ việc chép file extension vào thư mục PostgreSQL cần quyền Windows Administrator. Bước tạo DB bên dưới dùng quyền PostgreSQL riêng; hai loại quyền khác nhau.

Trong terminal thông thường:

```powershell
.\.venv\Scripts\python.exe .\scripts\bootstrap_database.py
```

Nhập mật khẩu tài khoản PostgreSQL `postgres` tại prompt ẩn. Mật khẩu quản trị không được ghi lại. Script tạo role `healthcare_app` với mật khẩu ngẫu nhiên, database `healthcare_dev`, bật extension và lưu DATABASE_URL của ứng dụng vào `.env` local. Tài khoản ứng dụng không có SUPERUSER/CREATEDB/CREATEROLE. Nếu role/database đã tồn tại, script giữ nguyên mật khẩu, dữ liệu và owner; nếu không khớp thì dừng để bạn xem xét.

Nếu đã tự tạo DB, điền DATABASE_URL đúng vào `.env` và bật extension bằng tài khoản PostgreSQL có quyền:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Không đổi `pg_hba.conf` sang trust và không reset password để vượt qua lỗi đăng nhập. Mở pgAdmin để quản trị server hiện tại.

## Alembic và kiểm tra DB

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe .\scripts\check_database.py
```

Revision `0001_enable_pgvector` chỉ enable extension; `0002_create_business_schema` tạo 14 bảng và `document_chunks.embedding VECTOR(1024)`; `0003_phase2_invariants` tăng cường invariant Phase 2. Phase 8 thêm `0004_add_json_document_type` để JSON/JSONL trở thành source được quản trị chính thức. Ba revision cũ không bị sửa. Dimension 1024 đã được xác minh bằng model BGE-M3 thật và kiểm tra runtime.

Seed synthetic, idempotent:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_demo.py
```

Seed dùng địa chỉ `.invalid`, password sentinel không đăng nhập được, một Appointment COMPLETED có MedicalRecord và một Appointment CONFIRMED. Để đăng nhập bằng Doctor/Staff/Admin demo, đặt mật khẩu Argon2 qua prompt ẩn; script chỉ nhận tài khoản synthetic `@example.invalid` và bị vô hiệu trong production:

```powershell
.\.venv\Scripts\python.exe .\scripts\set_demo_password.py doctor.an@example.invalid
.\.venv\Scripts\python.exe .\scripts\set_demo_password.py staff.demo@example.invalid
.\.venv\Scripts\python.exe .\scripts\set_demo_password.py admin.demo@example.invalid
```

SQLAlchemy engine dùng psycopg 3 và `pool_pre_ping`. `get_db()` cấp session theo request và đóng session khi kết thúc; service sẽ quyết định commit/transaction ở phase nghiệp vụ. Không gọi `Base.metadata.create_all()` để thay migration.

## Chạy và kiểm thử

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`GET /api/v1/health` trả đúng ba trường công khai: `status`, `application`, `environment`. Endpoint thực hiện `SELECT 1` và kiểm tra extension vector; chưa sẵn sàng trả 503 thay vì báo thành công giả. Swagger tại `/docs`, OpenAPI tại `/openapi.json`.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check

# Chỉ sau khi database thật đã sẵn sàng:
$env:RUN_DB_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:\RUN_DB_INTEGRATION
```

Unit tests dùng session override và cấu hình test riêng. Chỉ bật `RUN_DB_INTEGRATION=1` khi chủ động kiểm thử DB development đã migrate và seed; khi bật, lỗi DB sẽ fail. Test Phase 2 dùng transaction rollback cho dữ liệu tạm, không để lại bản ghi kiểm thử.

Phase 6 bổ sung `tests/test_phase6_business_mvp_integration.py`: concurrent booking bằng nhiều PostgreSQL session, schedule-overlap race, adjacent ranges, appointment transitions, cancellation boundary và authenticated Business/MedicalRecord E2E. Toàn bộ 51/51 Backend tests PASS với `RUN_DB_INTEGRATION=1`.

Automated regression mock các dịch vụ ngoài nên không phụ thuộc Gemini quota/network hoặc tải model. Kết quả nghiệm thu Phase 13 là 160/160 Backend test PASS với PostgreSQL integration. Test tích hợp pgvector dùng PostgreSQL thật khi bật `RUN_DB_INTEGRATION=1`; benchmark BGE/reranker và real Gemini/microphone smoke là kiểm tra tách riêng.

## Phase 13 security hardening

Các endpoint tốn tài nguyên/nhạy cảm (`register`, `login`, `refresh`, chat, document ingestion và Voice transcription) dùng rate limiter in-process có key đã hash và giới hạn tối đa 10.000 bucket. Cấu hình mặc định phù hợp một Backend instance Windows/demo và không cần Redis:

```dotenv
RATE_LIMIT_ENABLED=true
LOGIN_RATE_LIMIT=10
LOGIN_RATE_WINDOW_SECONDS=300
REGISTER_RATE_LIMIT=5
REFRESH_RATE_LIMIT=30
CHAT_RATE_LIMIT=30
VOICE_RATE_LIMIT=10
INGESTION_RATE_LIMIT=5
COMMON_RATE_WINDOW_SECONDS=60
```

Production bắt buộc bật rate limit, HTTPS origin, Secure cookie, JWT secret riêng và tắt DEV auth. Nếu scale nhiều Backend instance, cấu hình thêm shared rate limit ở hosting platform/reverse proxy vì limiter trong process không đồng bộ giữa các process. Response 429 giữ error contract và `Retry-After`. Unexpected exception trả JSON 500 đã sanitize; API thêm `nosniff`, `DENY`, `no-referrer`, permissions policy và HSTS khi production.

Dependency security được kiểm tra bằng:

```powershell
uvx pip-audit -r requirements.txt
npm.cmd audit --audit-level=moderate
```

Phase 13 nâng `PyJWT` lên 2.15.0, `python-multipart` lên 0.0.31 và transitive `fast-uri` lên 3.1.9. Kết quả cuối: không còn advisory được hai audit tool phát hiện.

Không commit `.env` thật. Không đặt DATABASE_URL vào Alembic INI hoặc frontend. `.env.example` chỉ chứa placeholder. `FRONTEND_ORIGIN` là một origin chính xác, mặc định `http://localhost:5173`; allow-credentials không dùng wildcard.

## Authentication API Phase 5

- `POST /api/v1/auth/register`: đăng ký Patient, bắt buộc email/password/full_name/phone; đồng thời tạo phiên.
- `POST /api/v1/auth/login`: đăng nhập case-insensitive theo email, chỉ User ACTIVE.
- `POST /api/v1/auth/refresh`: rotate refresh token, lưu hash, phát hiện reuse và revoke session family.
- `POST /api/v1/auth/logout`: revoke refresh session và xóa cookie.
- `GET /api/v1/auth/me`: khôi phục phiên và trả User/roles hiện hành từ PostgreSQL.
- `PATCH /api/v1/users/me`: cập nhật profile; Patient không được xóa phone.

Các request thay đổi trạng thái bằng cookie phải gửi `Origin` đúng và `X-CSRF-Token`. Access JWT chỉ mang identity tối thiểu; User ACTIVE và role được kiểm tra lại từ DB để tạo `ActorContext`. Production bắt buộc HTTPS origin, Secure cookie, JWT secret riêng và `DEV_AUTH_ENABLED=false`. Frontend và Backend local đều dùng hostname `localhost` để SameSite cookie hoạt động nhất quán.

## Gemini + RAG Phase 8/12

Thêm vào `.env` local, không commit key:

```dotenv
GEMINI_API_KEY=YOUR_LOCAL_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=20
```

`POST /api/v1/chat/messages` nhận text + history ngắn hạn. Endpoint dùng auth/cookie/CSRF hiện có; Gemini key chỉ ở Backend. Không có database chat, Voice hoặc quyền đọc MedicalRecord.

Phase 8 giữ endpoint trên và mở rộng response thành `{ "answer": "...", "sources": [...] }`. Mặc định request dùng RAG; có thể đặt `use_rag=false` để giữ text-chat Phase 7. Corpus chỉ gồm `Document` ở trạng thái `APPROVED` và ingestion `COMPLETED`; MedicalRecord, Appointment và dữ liệu lâm sàng riêng tư không nằm trong đường truy xuất.

Phase 9 mở rộng response bằng `tool_results` và `booking_confirmation`. Tools chỉ gọi `SpecialtyService`, `DoctorService`, `ScheduleService`, `AppointmentService` và `HandoffService`; model không gửi identity và không truy cập ORM/SQL. `create_booking` chỉ sinh confirmation token ngắn hạn gắn actor + slot. Chỉ `POST /api/v1/chat/bookings/confirm` sau thao tác bấm nút mới gọi transaction booking thật.

Phase 10 thêm `risk_alert`. Risk engine deterministic chạy trước RAG/Gemini, dùng tập rule demo cố định, không query MedicalRecord và không được coi là chẩn đoán. Khi trigger, hệ thống trả cảnh báo cố định và tạo handoff `URGENT` qua HandoffService; reason chỉ lưu mã rule, không lưu nguyên văn message.

Sau khi tự điền key trong `.env`, xác minh model và một generation thật:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_gemini.py
```

Key/model thiếu hoặc Gemini lỗi chỉ làm chat endpoint trả phản hồi có kiểm soát; Health và Business MVP vẫn hoạt động.

### Dataset và ingestion

Supported sources: JSON/JSONL, CSV UTF-8, PDF có text bằng PyMuPDF và DOCX bằng python-docx. Không OCR ở RAG V1. Folder `data/rag/raw` và `data/rag/processed` được giữ bằng `.gitkeep`; mọi dataset thực bị Git ignore.

Dataset chính: `mtue29/vietnamese-medical-dataset`. Full file dự kiến tại `data/rag/raw/vietnamese-medical-dataset.json`. Không tải mirror và không commit file này. Tải subset chính thức để smoke hoặc tải full một cách chủ động:

```powershell
.\.venv\Scripts\python.exe .\scripts\download_rag_dataset.py --subset 20
# Hoặc, cần khoảng 1 GB dung lượng tải và thêm tài nguyên xử lý:
.\.venv\Scripts\python.exe .\scripts\download_rag_dataset.py --full
.\.venv\Scripts\python.exe .\scripts\inspect_rag_dataset.py `
  .\data\rag\raw\vietnamese-medical-dataset.json --file-type JSON
```

Đăng ký source qua đúng Document approval workflow, sau đó ingest bằng lệnh tách khỏi Backend startup. Lấy `document_id` từ output lệnh đầu:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_rag_document.py `
  --source .\data\rag\raw\vietnamese-medical-dataset.subset.jsonl `
  --actor-email admin.demo@example.invalid `
  --title "Vietnamese Medical Dataset — Official Smoke Subset"

.\.venv\Scripts\python.exe .\scripts\ingest_rag_dataset.py `
  --document-id <DOCUMENT_ID> `
  --actor-email admin.demo@example.invalid `
  --source .\data\rag\raw\vietnamese-medical-dataset.subset.jsonl `
  --batch-size 8
```

Thêm `--dry-run` để đếm source/chunk mà không embedding; `--limit N` cho smoke từ file lớn. File ingest phải nằm trong `data/rag/raw`, đúng loại và đúng SHA-256 đã được duyệt. Re-ingest cùng Document thay thế chunk cũ trong transaction, không cộng dồn. BGE-M3 chạy CPU trên Windows, batch configurable qua `EMBEDDING_BATCH_SIZE`; lần đầu tải model sẽ tốn thời gian và cache cục bộ.

Đánh giá exact baseline sau ingestion:

```powershell
.\.venv\Scripts\python.exe .\scripts\evaluate_rag_v1.py
```

Retriever exact baseline dùng cosine distance + Top-K và `SET LOCAL enable_indexscan=off`; script kiểm tra `EXPLAIN` không chọn HNSW. HNSW index được reuse trong benchmark Phase 12 và là final runtime strategy sau phép so sánh. Nếu không có chunk đủ gần, chatbot trả no-context fallback và không bịa source.

### RAG V2/V3 và benchmark Phase 12

Phase 12 không tạo RAG hoặc vector store thứ hai. `RAGService` chọn retrieval strategy qua `RAG_STRATEGY`:

- `exact_dense`: baseline Phase 8, exact cosine Top-K.
- `hnsw_dense`: approximate dense search qua HNSW cosine index hiện có.
- `hybrid_rrf`: HNSW Dense + BM25 trên cùng `document_chunks`, hợp nhất bằng Reciprocal Rank Fusion.
- `hybrid_rerank`: Hybrid RRF, sau đó BGE reranker chỉ trên candidate set.

Cấu hình mặc định cuối là `hnsw_dense`. Cấu hình tập trung trong `.env`; không hard-code strategy ở router/chat service:

```dotenv
RAG_STRATEGY=hnsw_dense
RAG_DENSE_CANDIDATES=20
RAG_SPARSE_CANDIDATES=20
RAG_RRF_K=60
RAG_HNSW_EF_SEARCH=40
RAG_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RAG_RERANKER_DEVICE=cpu
RAG_RERANKER_BATCH_SIZE=4
RAG_RERANK_CANDIDATES=20
```

BM25 chuẩn hóa Unicode NFC, `casefold`, tách token chữ/số bằng regex Unicode và giữ nguyên dấu tiếng Việt. Production có fallback rõ ràng về exact dense nếu HNSW/BM25/reranker lỗi; experiment mode tắt fallback để không che lỗi benchmark. Mọi strategy chỉ truy vấn Document `APPROVED` + ingestion `COMPLETED`, giữ source metadata và không có đường truy cập MedicalRecord.

Chuẩn bị large controlled subset deterministic (không phải full dataset), tạo fixed evaluation set và benchmark:

```powershell
.\.venv\Scripts\python.exe .\scripts\download_rag_dataset.py --large-subset 400
.\.venv\Scripts\python.exe .\scripts\build_rag_evaluation.py `
  .\data\rag\raw\vietnamese-medical-dataset.large-400.jsonl `
  --output .\app\rag\evaluation_phase12.json --limit 50

# Sau prepare/approve/ingest bằng workflow Document hiện có:
.\.venv\Scripts\python.exe .\scripts\evaluate_rag_phase12.py `
  --strategies exact_dense hnsw_dense hybrid_rrf hybrid_rerank `
  --output-json .\data\rag\processed\phase12-results.json `
  --output-csv .\data\rag\processed\phase12-results.csv
```

Benchmark chính dùng 400 raw records deterministic, 199 nội dung/chunk unique sau dedup, 50 query grounded, BGE-M3 1024 chiều và Top-K=5 cho mọi strategy. PostgreSQL development còn 10 smoke chunks Phase 8, vì vậy corpus DB được truy vấn thực tế là 209 chunks; cả bốn strategy dùng đúng cùng corpus đó. Kết quả và phương pháp đầy đủ nằm trong `docs/phase-12.md` và `docs/phase-12-results.*`.

V3 dùng `BAAI/bge-reranker-v2-m3` trên CPU Windows. Lần đầu có thể phải tải model; benchmark ghi cả thời gian load lạnh. Trên máy demo, V3 tăng Hit/Recall@5 từ 0,96 lên 0,98 nhưng median khoảng 8,2 giây, nên không được chọn làm runtime mặc định.

## API nghiệp vụ Phase 3

- `/api/v1/specialties`: list/detail/create/update/status.
- `/api/v1/doctors`: list/detail/filter theo specialty/create/update.
- `/api/v1/schedules`: schedule không hard-delete, slot generation, available slots, block/unblock.
- `/api/v1/appointments`: booking, list/detail, cancel và Doctor cập nhật COMPLETED/NO_SHOW.
- `/api/v1/medical-records`: create/get/update/history; không có DELETE.
- `/api/v1/documents`: metadata CRUD, Admin review và `POST /{document_id}/ingest`; DELETE chỉ cho metadata PENDING chưa ingest/chưa có chunk.
- `/api/v1/handoffs`: ticket create/list/detail/state update.
- `WS /api/v1/handoffs/ws`: Staff/Admin notification/status metadata; PostgreSQL/REST vẫn authoritative.
- `POST /api/v1/voice/transcriptions`: audio push-to-talk → faster-whisper Vietnamese transcript; audio tạm được cleanup.

Business error dùng payload `{"error":{"code":"...","detail":"..."}}`. HTTP 400/401/403/404/409 do service/error handler quản lý; Pydantic trả 422; lỗi ngoài dự kiến được exception handler tập trung chuyển thành JSON 500 đã sanitize, không trả stack trace, provider detail hoặc secret.

## Development identity tùy chọn

Trong `development` hoặc `test`, có thể bật `DEV_AUTH_ENABLED=true` để dùng `X-Dev-User-Id` cho kiểm thử nội bộ. Backend vẫn kiểm tra User ACTIVE và đọc role từ PostgreSQL. JWT lỗi không fallback sang header DEV và production bắt buộc tắt cơ chế này. Cookie/JWT là đường xác thực chính của Phase 5.

MedicalRecord chỉ cho Doctor phụ trách tạo/cập nhật Appointment COMPLETED; Patient chỉ đọc hồ sơ của chính mình; Staff/Admin không có quyền đọc lâm sàng mặc định. Audit không lưu symptoms, notes, conclusion hoặc instructions.
