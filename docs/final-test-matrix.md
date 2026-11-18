# Final Test Matrix

Evidence lịch sử Phase 14 được chạy ngày 02/11/2026 và post-checkpoint workflow ngày 06/11/2026. Current final regression cho ENH-KB-001 được ghi nhận ngày 18/11/2026. Môi trường: Windows development, PostgreSQL local thật, pgvector thật. External provider/hardware tests không bị mô tả như browser automation đầy đủ.

## Current final verification — ENH-KB-001

| Area | Scope | Current result |
| --- | --- | --- |
| Backend full regression | PostgreSQL integration và toàn bộ application regression | **191 passed** |
| Frontend full regression | Vitest/React Testing Library | **54 passed** |
| Frontend KB-001C targeted | Doctor contribution + Admin review/ingest UI | **8 passed** |
| Backend contribution/download targeted | upload, ownership, validation, safe download, compensation | **19 passed** |
| Backend contribution + RAG integration | lifecycle, ingest, pgvector chunks, retrieval filter/assertion | **25 passed** |
| Browser Golden Path + release suite | full non-AI workflow, KB-001C Golden Path và release smoke | **5/5 passed** |
| Migration current/head | applied schema | `0005_document_contribution`; exactly one head |
| Migration drift | model metadata vs DB | **PASS**, no new upgrade operations |
| Static/release gates | ESLint, production build, compileall, pip check | **PASS** |

Golden Path đã xác minh Doctor upload tài liệu synthetic, Admin reject kèm lý do, Doctor resubmit, Admin approve, tài liệu chưa retrievable trước ingest, sau đó ingest bằng BGE-M3 vào PostgreSQL/pgvector và retriever trả đúng marker/document id/title. Patient/Staff không quản lý corpus. Evidence này không yêu cầu live Gemini và không khẳng định full dataset 1 GB đã được ingest.

## Historical Phase 14 and post-checkpoint evidence

| Area | Scope | Command / evidence | Final result |
| --- | --- | --- | --- |
| Backend full regression | Unit + PostgreSQL integration, Auth, business, concurrency, MedicalRecord, Documents/RAG, AI/Tools/Risk, Handoff, Voice, Doctor provisioning/Schedule workflow | `RUN_DB_INTEGRATION=1; python -m pytest` | **162/162 PASS** in 13.32s (06/11/2026) |
| Python syntax | `app` + `scripts` | `python -m compileall -q app scripts` | **PASS** |
| Python dependency consistency | installed environment | `python -m pip check` | **PASS**, no broken requirements |
| Python vulnerability audit | pinned `requirements.txt` | `uvx pip-audit -r requirements.txt` | **PASS**, no known vulnerabilities |
| Frontend component/unit | 8 Vitest files | `npm test` | **41/41 PASS** (06/11/2026) |
| Frontend static quality | source/config | `npm run lint` | **PASS**, 0 warnings |
| Frontend production build | TypeScript + Vite | `npm run build` | **PASS**, largest JS 398.03 kB; no >500 kB warning |
| Browser workflow + release smoke | Edge, real Backend/Frontend/PostgreSQL on ports 8013/5174; full non-AI multi-role golden path + scoped release smoke | `npm run test:e2e` | **4/4 PASS** in 58.5s (06/11/2026) |
| Production npm dependency audit | runtime dependencies only | `npm audit --omit=dev --audit-level=moderate` | **PASS**, 0 vulnerabilities |
| High-severity npm gate | all dependencies | `npm audit --audit-level=high` | **PASS**, no Critical/High open |
| Development npm audit | ESLint/minimatch toolchain | `npm audit` | **12 MODERATE accepted**, production impact 0; no `--force` breaking downgrade |
| Migration current/head | applied schema tại thời điểm Phase 14 | `alembic current`; `alembic heads` | `0004_add_json_document_type (head)` |
| Migration drift | model metadata vs DB | `alembic check` | **PASS**, no new upgrade operations |
| Database runtime | PostgreSQL/SQLAlchemy/pgvector/vector dimension/cosine | `scripts/check_database.py` | **PASS**: PostgreSQL 18.6, pgvector 0.8.7, Alembic 0004 |
| Seed idempotency | synthetic demo seed twice | `scripts/seed_demo.py` ×2 | **PASS** both runs |
| Requirement coverage | all SRS v1.1 identifiers vs final matrix | extraction from DOCX + identifier comparison | **159/159 represented** |
| Dataset ignore | full/subset files under `data/rag` | `git check-ignore -v` | **PASS**; `.gitkeep` remains allowed |
| Secret scan | common key/URL/token patterns excluding local `.env` and dependency/build folders | recursive source scan | **PASS with synthetic-test matches reviewed**; no real key identified |

## Critical behavior coverage

| Behavior | Evidence | Result |
| --- | --- | --- |
| Concurrent booking | five PostgreSQL transactions target one slot; only one succeeds | PASS |
| Schedule overlap race | advisory transaction lock by Doctor; overlap serialized; adjacent ranges accepted | PASS |
| Appointment state/cancel | CONFIRMED → CANCELLED/COMPLETED/NO_SHOW; invalid transitions rejected; slot consistency | PASS |
| MedicalRecord privacy | COMPLETED-only, ownership, duplicate conflict, own-read, Staff/Admin denial, metadata-only audit | PASS |
| Auth/session security | Argon2, access/refresh, rotation/reuse/logout, CSRF/Origin/CORS, production dev-auth guard | PASS |
| RAG governance | APPROVED-only, format loaders, dedup/re-ingest, sources/no-context, MedicalRecord isolation | PASS |
| Tool booking | ActorContext identity, structured validation, business service reuse, explicit confirmation | PASS |
| Risk Alert | deterministic rule-first positive/negative/false-positive cases and handoff | PASS |
| Handoff | REST/PostgreSQL authoritative; WebSocket notification/reconnect/failure | PASS |
| Voice | upload/format/size/empty/STT failure/temp cleanup and text/TTS fallback | PASS functionality; live Vietnamese accuracy remains limited |

## Playwright scope boundary

Current suite có full non-AI multi-role Business Golden Path, KB-001C Doctor contribution Golden Path và scoped release-smoke, tổng cộng 5/5. Suite không claim live Gemini provider, Voice/STT hardware, full 1 GB corpus hoặc exhaustive WebSocket timing automation; các phần này nằm ngoài verification scope hoặc có evidence riêng.

