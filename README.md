# Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn

Phase 1-14 đã PASS. Codebase đã được chốt cho phạm vi đồ án/demo có kiểm soát; không thêm feature mới sau mốc này, trừ bug fix bắt buộc kèm regression. Hệ thống hiện có Business MVP, Gemini + RAG (pgvector), Tool Calling + Risk Alert, Voice push-to-talk tiếng Việt và Handoff notification/status bằng WebSocket. Phát triển trên Windows 11 bằng PowerShell; Frontend và Backend là hai project độc lập.

```text
DO_AN_Y_TE/
├── healthcare-backend/     Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic
├── healthcare-frontend/    React + TypeScript + Vite + Material UI
├── docs/
│   ├── SRS_FINAL.docx
│   ├── de-cuong/
│   ├── phase-1.md
│   ├── phase-2.md
│   ├── phase-2-final-audit.md
│   ├── phase-3.md
│   ├── phase-4.md
│   ├── phase-5.md
│   ├── phase-6.md
│   ├── phase-7.md
│   ├── phase-8.md
│   ├── phase-9.md
│   ├── phase-10.md
│   ├── phase-11.md
│   ├── phase-12.md
│   ├── phase-13.md
│   ├── phase-14.md
│   ├── database-design.md
│   ├── data-dictionary.md
│   ├── final-architecture-diagrams.md
│   ├── final-requirement-matrix.md
│   ├── final-test-matrix.md
│   ├── final-security-findings.md
│   ├── final-rag-dataset-performance.md
│   ├── migration-list.md
│   ├── demo-script.md
│   ├── defense-notes.md
│   ├── screenshot-checklist.md
│   ├── known-issues-tracker.md
│   └── requirement-traceability.md
└── README.md
```

SRS v1.1 Final trong `docs/SRS_FINAL.docx` là baseline yêu cầu triển khai. Bản v1.0 được lưu tại `docs/backups/`. Đề cương đã nộp trong `docs/de-cuong/` xác định phạm vi nghiên cứu và không bị chỉnh sửa. Mỗi thay đổi requirement tiếp theo cần Change Request; không sửa tài liệu để khớp code.

## Chuẩn bị

- Windows 11 x64, VS Code, PowerShell, Git.
- Python 3.12. Kiểm tra bằng `py -3.12 --version`. Nếu launcher không nhận Python do uv quản lý, dùng `uv python find 3.12` để lấy đường dẫn rồi truyền vào script setup.
- Node.js tương thích `engines` trong frontend (máy kiểm thử dùng Node 22.23.1).
- PostgreSQL x64 chạy Windows Service và pgAdmin. Cài pgvector tương ứng đúng major version PostgreSQL theo hướng dẫn backend.

Không cần Gemini, BGE-M3, Voice hoặc WebSocket để chạy Business MVP Phase 6. Chatbot RAG cần `GEMINI_API_KEY`, `GEMINI_MODEL`, BGE-M3 và corpus đã được Admin duyệt/ingest. Voice STT dùng faster-whisper trên Backend; lần đầu dùng sẽ tải model cấu hình.

## Khởi tạo backend

Tại thư mục root:

```powershell
cd .\healthcare-backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Nếu Python 3.12 chỉ được uv quản lý:

```powershell
$python312 = uv python find 3.12
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -PythonPath $python312
```

Khởi tạo development database bằng script có nhập mật khẩu quản trị ẩn. Không gửi mật khẩu vào chat hoặc đưa vào command line:

```powershell
.\.venv\Scripts\python.exe .\scripts\bootstrap_database.py
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe .\scripts\check_database.py
.\.venv\Scripts\python.exe .\scripts\seed_demo.py
```

Hoặc dùng một lệnh tương tác để chạy cả bootstrap, migration và kiểm tra:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\initialize_database.ps1
```

Script bootstrap tạo tài khoản riêng `healthcare_app` và database `healthcare_dev` nếu chưa tồn tại; không reset mật khẩu hoặc thay đổi quyền của tài khoản hiện có. Nó ghi kết nối của tài khoản ứng dụng vào `.env` local. Nếu pgvector chưa được cài trên server, script dừng trước khi tạo role/database và chỉ rõ cách xử lý.

## Chạy hai terminal

Terminal 1 — backend:

```powershell
cd .\healthcare-backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 — frontend:

```powershell
cd .\healthcare-frontend
npm.cmd ci
Copy-Item .env.example .env
npm.cmd run dev
```

Chỉ copy `.env.example` ở lần đầu nếu chưa có `.env`; giữ cấu hình đã điền ở những lần chạy sau.

- Web: <http://localhost:5173>
- API health: <http://localhost:8000/api/v1/health>
- Swagger: <http://localhost:8000/docs>
- Database: Windows Service PostgreSQL đang cài trên máy.

Health trả `200` khi kết nối SQLAlchemy và extension vector đều sẵn sàng; trả `503` với thông báo tổng quát khi chưa sẵn sàng. Không trả connection string, mật khẩu hoặc stack trace.

## Kiểm thử

```powershell
# Trong healthcare-backend
.\.venv\Scripts\python.exe -m pytest
$env:RUN_DB_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:\RUN_DB_INTEGRATION

# Trong healthcare-frontend
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e
```

Unit tests không yêu cầu database. Integration tests cần database thật đã bootstrap và migrate; khi bật cờ integration, lỗi kết nối sẽ làm test fail, không bị bỏ qua.

## Git

Một repository tại root; dependency và môi trường của hai project vẫn độc lập. Dùng nhánh `main` ổn định, tạo nhánh ngắn như `phase-1/foundation` hoặc `feature/<ten-chuc-nang>` cho công việc, review rồi merge. Commit source, migrations, lockfile và tài liệu; không commit `.env`, `.venv`, `node_modules` hoặc dữ liệu local. Chưa cấu hình GitHub remote hay push trong Phase 1.

Thiết kế database nằm trong `docs/database-design.md` và `docs/data-dictionary.md`. Báo cáo triển khai nằm trong `docs/phase-1.md` đến `docs/phase-14.md`; bộ tài liệu demo/bảo vệ cuối nằm trong các file `docs/final-*`, `docs/demo-script.md`, `docs/defense-notes.md` và `docs/screenshot-checklist.md`.

Dataset chính là `mtue29/vietnamese-medical-dataset` trên Hugging Face. File full dự kiến là `healthcare-backend/data/rag/raw/vietnamese-medical-dataset.json` và bị Git ignore. Bằng chứng Phase 12/13 chỉ dùng **large controlled subset**: 400 raw records, 199 nội dung/chunk mới sau dedup và 209 chunks trong database benchmark; không được mô tả là đã ingest toàn bộ dataset khoảng 1 GB. Cách tải/ingest lại nằm trong `healthcare-backend/README.md`.

Voice đã chạy theo pipeline microphone browser → MediaRecorder → faster-whisper → transcript → chat hiện có, nhưng độ chính xác STT tiếng Việt trên máy demo là known limitation. Business MVP vẫn hoạt động khi Gemini, RAG, Voice hoặc WebSocket không khả dụng.
