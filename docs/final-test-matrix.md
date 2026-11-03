# Final Test Matrix

Ngày chạy final regression: 02/11/2026. Môi trường: Windows development, PostgreSQL local thật, pgvector thật. External provider/hardware tests không bị mô tả như browser automation đầy đủ.

| Area | Scope | Command / evidence | Final result |
| --- | --- | --- | --- |
| Backend full regression | Unit + PostgreSQL integration, Auth, business, concurrency, MedicalRecord, Documents/RAG, AI/Tools/Risk, Handoff, Voice | `RUN_DB_INTEGRATION=1; python -m pytest` | **160/160 PASS** in 21.09s |
| Python syntax | `app` + `scripts` | `python -m compileall -q app scripts` | **PASS** |
| Python dependency consistency | installed environment | `python -m pip check` | **PASS**, no broken requirements |
| Python vulnerability audit | pinned `requirements.txt` | `uvx pip-audit -r requirements.txt` | **PASS**, no known vulnerabilities |
| Frontend component/unit | 7 Vitest files | `npm test` | **37/37 PASS** |
| Frontend static quality | source/config | `npm run lint` | **PASS**, 0 warnings |
| Frontend production build | TypeScript + Vite | `npm run build` | **PASS**, largest JS 398.03 kB; no >500 kB warning |
| Scoped browser smoke | Edge, real Backend/Frontend/PostgreSQL on ports 8013/5174 | `npm run test:e2e` | **3/3 PASS** in 12.9s |
| Production npm dependency audit | runtime dependencies only | `npm audit --omit=dev --audit-level=moderate` | **PASS**, 0 vulnerabilities |
| High-severity npm gate | all dependencies | `npm audit --audit-level=high` | **PASS**, no Critical/High open |
| Development npm audit | ESLint/minimatch toolchain | `npm audit` | **12 MODERATE accepted**, production impact 0; no `--force` breaking downgrade |
| Migration current/head | applied schema | `alembic current`; `alembic heads` | `0004_add_json_document_type (head)` |
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

The 3 browser tests are a **scoped release smoke**, not full automation of multi-role mutations, live Gemini quota/network, WebSocket timing or physical microphone permission. Those areas have backend integration/component tests and historical/manual evidence, but are not claimed as full Playwright coverage.

