# Phase 1 Project Foundation

Ngày thực hiện: 17/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

Trạng thái hiện tại: **DONE — đã kiểm chứng đầy đủ 13/13 điều kiện Phase 1**, bao gồm database thật, pgvector, SQLAlchemy, Alembic online, 16 tests pass và React nhận health HTTP 200 từ FastAPI. Không chuyển sang Phase 2.

## Căn cứ và requirements

Đã đọc SRS v1.0 FINAL và đề cương đã nộp. Phase 1 hiện thực nền tảng cho NFR-MNT-01, NFR-MNT-02, NFR-COMP-01, NFR-TEST-01; phần cấu hình/CORS/che secret của NFR-SEC-02..04; và trạng thái UI của NFR-USAB-01. Các FR nghiệp vụ, RBAC, booking, RAG, Voice và tiêu chí Business/AI MVP chưa được coi là hoàn thành.

Các actor, Use Case, acceptance criteria và business rules đã được đối chiếu để xác định ranh giới phase. Không tạo API nghiệp vụ có quyền, bảng business, model embedding hoặc module AI trong foundation. Chi tiết mapping nằm trong `requirement-traceability.md`; không sửa nội dung SRS hay đề cương.

## Những gì đã làm

- Tạo Git repository `DO_AN_Y_TE`, nhánh `main`, frontend/backend độc lập, có environment, dependency và quy trình chạy riêng.
- Sao chép nguyên trạng SRS vào `docs/SRS_FINAL.docx`, đề cương vào `docs/de-cuong/`. Giữ lại các bản gốc ở thư mục cha.
- Tạo `.venv` bằng Python 3.12.14 đã có trên máy, cài các dependency foundation và lưu `requirements.lock.txt`.
- FastAPI có cấu hình environment, OpenAPI, exact-origin CORS và health qua SQLAlchemy.
- SQLAlchemy 2 có lazy engine, session factory và dependency session theo request.
- Alembic có config lấy URL từ backend và revision infrastructure đầu tiên; đã sinh offline SQL.
- Dựng React/TypeScript/Vite, Material UI, TanStack Query, Axios, React Router và màn hình health. Cài React Hook Form, Zod, resolver theo stack, chưa dựng form nghiệp vụ.
- Pin phiên bản frontend và lưu package-lock để dùng `npm ci`.
- Cài Microsoft C++ Build Tools 2022 17.14.42 từ nguồn Microsoft qua winget, build pgvector v0.8.7 từ source chính thức cho PostgreSQL 18.6 x64 và cài server files thành công.
- Đã bootstrap development role/database bằng mật khẩu quản trị nhập ẩn, sinh mật khẩu ứng dụng riêng, enable pgvector, chạy migration và kiểm tra DB thật thành công.
- Khởi động lại tiến trình FastAPI sau khi bootstrap để nạp DATABASE_URL mới; xác nhận health HTTP 200 và giao diện hiển thị kết nối thành công.

## File tạo và sửa

Tất cả source dưới root mới là file mới. Không sửa source hoặc tài liệu cũ ở thư mục cha. Trong quá trình dựng đã cập nhật file mới để pin dependency, dùng HTTPX ASGITransport phù hợp với Starlette hiện tại và không hiển thị health success cũ sau lần kiểm tra bị lỗi.

Lượt nghiệm thu cuối chỉ cập nhật `docs/phase-1.md`, `docs/requirement-traceability.md` và khởi động lại tiến trình backend để nạp cấu hình; không thay đổi source nghiệp vụ hoặc nội dung SRS/đề cương.

| Nhóm | File mới |
| --- | --- |
| Root | README.md, .gitignore, .gitattributes |
| Backend config | .env.example, .gitignore, requirements.txt, requirements.lock.txt, pytest.ini, README.md |
| Backend app | app/main.py, app/api/v1/router.py, app/core/config.py, app/core/database.py và các __init__.py |
| Migration | alembic.ini, migrations/env.py, migrations/script.py.mako, migrations/versions/0001_enable_pgvector.py |
| Scripts | scripts/setup.ps1, install_pgvector.ps1, bootstrap_database.py, initialize_database.ps1, check_database.py |
| Backend tests | tests/conftest.py, test_health.py, test_config.py, test_bootstrap.py, test_database_integration.py |
| Backend local data | data/.gitkeep; log/screenshot local và .env/.venv được Git ignore |
| Frontend config | package.json, package-lock.json, index.html, vite.config.ts, tsconfig.json, tsconfig.app.json, tsconfig.node.json, eslint.config.js, .env.example, .gitignore, README.md |
| Frontend source | src/main.tsx, App.tsx, app/AppProviders.tsx, app/queryClient.ts, api/client.ts, api/health.ts, hooks/useHealth.ts, types/health.ts, components/HealthStatus.tsx, pages/HomePage.tsx, routes/router.tsx, theme/theme.ts, vite-env.d.ts |
| Thư mục dự phòng | public/, src/features/, src/utils/ có .gitkeep |
| Docs | Bản sao SRS/đề cương, phase-1.md, requirement-traceability.md |

## Database migration

`0001_enable_pgvector` chạy `CREATE EXTENSION IF NOT EXISTS vector` và cập nhật version Alembic. Chưa có schema nghiệp vụ. Downgrade giữ extension để không xóa dữ liệu vector ngoài ý muốn.

Offline SQL đã sinh thành công. Online `alembic upgrade head` và `alembic current` đã chạy thành công bằng kết nối thật; revision hiện tại là `0001_enable_pgvector (head)`. Đã xác nhận extension vector 0.8.7 được enable trong development database, truy vấn cosine hoạt động và public schema chỉ có bảng `alembic_version`. Không thực hiện downgrade trong lượt nghiệm thu này.

## Endpoint và UI

| Thành phần | Kết quả |
| --- | --- |
| GET /api/v1/health | Ba trường status/application/environment; 200 khi DB + vector sẵn sàng, 503 nếu chưa sẵn sàng; không lộ secret |
| /docs và /openapi.json | Swagger và schema OpenAPI của FastAPI |
| Frontend / | Tiêu đề đề tài đúng nguyên văn, health loading/error/success, nút kiểm tra lại |
| API nghiệp vụ / Auth / AI | Chưa triển khai trong Phase 1 |

## Commands đã chạy

Tại root mới:

```powershell
git init -b main
git status --short --untracked-files=all
git check-ignore healthcare-backend/.env healthcare-frontend/.env
```

Backend:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -PythonPath 'C:\Users\Nao\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none\python.exe'
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q app scripts migrations tests
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
.\.venv\Scripts\python.exe -m alembic history
$env:RUN_DB_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest
Remove-Item Env:\RUN_DB_INTEGRATION
.\.venv\Scripts\python.exe .\scripts\check_database.py
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm.cmd install
npm.cmd install --package-lock-only --ignore-scripts
npm.cmd ci --ignore-scripts
npm.cmd install --save-dev --save-exact @types/node@22
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

Windows/pgvector:

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --accept-package-agreements --accept-source-agreements --silent --override "--wait --quiet --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
# Script sau đã chạy trong PowerShell Administrator:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_pgvector.ps1
```

Người dùng đã hoàn tất `scripts/initialize_database.ps1 -KeepOpen` qua cửa sổ PowerShell local. File kết quả không chứa secret tại `data/database-setup-result.json` có trạng thái `ready`. Sau đó đã kiểm tra độc lập kết nối DB, chạy đủ tests và khởi động lại FastAPI để dùng cấu hình mới.

## Tests và kết quả

| Kiểm tra | Kết quả đã xác nhận |
| --- | --- |
| Pytest unit | 14 passed |
| Pytest integration | 2 passed trên PostgreSQL development thật |
| Pytest toàn bộ với RUN_DB_INTEGRATION=1 | 16 passed, 0 skipped |
| pip check | No broken requirements found |
| Python compileall | Pass |
| Alembic offline SQL/history và online upgrade/current | Pass; revision 0001_enable_pgvector (head) |
| Frontend ESLint | Pass |
| TypeScript + Vite production build | Pass |
| npm audit trong cài dependency | 0 vulnerabilities tại thời điểm chạy |
| Browser smoke bằng Playwright với Edge headless | Đã kiểm tra đường lỗi 503 trước khi DB sẵn sàng và đường thành công 200 sau khi bootstrap/restart; React hiển thị đúng kết quả, nút thử lại hoạt động, không có JS runtime error |
| Mobile viewport 390 px | Không có horizontal overflow |
| CORS allowed/denied | Pass trong automated tests |
| Git ignore | .env/.venv/node_modules/dist/local logs bị ignore; source, migrations, .env.example và SRS vẫn được liệt kê |
| Tài liệu nguyên trạng | SHA-256 bản sao khớp bản gốc |
| pgvector build/install/enable | Pass: server files được cài cho PostgreSQL 18.6 x64; extension 0.8.7 và cosine distance được xác minh bằng SQL |
| SQLAlchemy + DB thật | Kết nối thành công với development DB; SELECT 1 pass |
| Health HTTP 200 + DB thật | Pass: status=ok, application=healthcare-backend, environment=development |
| Swagger HTTP | 200 |

SHA-256 SRS: `0F8CD753286E66D2060C9BF4FDA8D21F3161B301064A5573F468D283731916CB`.

SHA-256 đề cương: `8948955A837F3B296D282943EF6F39370163673136A1D996004E375AF460D978`.

## Issues và phần còn thiếu

Không còn blocker đối với các điều kiện nghiệm thu Phase 1. Mật khẩu quản trị đã được nhập trực tiếp tại terminal local; không reset password hoặc thay pg_hba.conf. Database, pgvector, migration và integration tests đều đã được xác minh.

Tiến trình FastAPI ban đầu giữ cấu hình cache từ trước khi bootstrap nên còn trả 503 dù DB đã sẵn sàng. Đã dừng đúng tiến trình do Phase 1 khởi chạy và chạy lại để nạp .env mới; health hiện trả 200. Đây là thay đổi cấu hình runtime, không cần sửa source.

Vite còn cảnh báo bundle foundation khoảng 539 kB (gzip khoảng 174 kB), vượt mốc cảnh báo mặc định 500 kB. Build vẫn thành công; chưa tăng ngưỡng hoặc thêm cấu hình chỉ để che cảnh báo. Đánh giá chia bundle theo route khi có các màn hình thực tế.

Chưa tạo GitHub remote, commit/push, auth, business schema hoặc AI; các phần này không nằm trong điều kiện hoàn thành Phase 1.

## Checklist nghiệm thu

- [x] DONE — healthcare-backend tồn tại độc lập.
- [x] DONE — healthcare-frontend tồn tại độc lập.
- [x] DONE — không trộn source BE/FE.
- [x] DONE — FastAPI chạy ở 127.0.0.1:8000.
- [x] DONE — React chạy ở localhost:5173.
- [x] DONE — React gọi được FastAPI, đã quan sát response thật.
- [x] DONE — PostgreSQL Windows Service đang chạy.
- [x] DONE — development DB được tạo và pgvector được enable/verify bằng SQL.
- [x] DONE — SQLAlchemy kết nối thành công với development DB thật.
- [x] DONE — online Alembic pipeline được kiểm chứng.
- [x] DONE — Pytest pass: 14 unit + 2 integration = 16 passed, không skip.
- [x] DONE — frontend lint/build pass.
- [x] DONE — SRS và đề cương nằm trong docs/ và nội dung không thay đổi.
- [x] DONE — health HTTP 200 và integration tests pass trước khi chốt Phase 1.

Phase 1 đã hoàn thành; toàn bộ điều kiện bắt buộc đã được kiểm chứng. Không tự động bắt đầu Phase 2.
