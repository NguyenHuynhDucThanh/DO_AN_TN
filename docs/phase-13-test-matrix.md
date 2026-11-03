# Phase 13 Test Matrix

Ngày chốt: 30/10/2026. SRS v1.1 là source of truth.

| Requirement / boundary | Module | Test / evidence | Result | Status |
| --- | --- | --- | --- | --- |
| Foundation và API health | Core/FastAPI/PostgreSQL | Full pytest; 50-request health sample; Playwright health | 160/160; health median 2,875 ms, p95 3,628 ms | PASS |
| Migration/model parity | Alembic/SQLAlchemy | `current`, `heads`, `check`, `check_database.py` | One head `0004`; no operations; PostgreSQL 18.6/pgvector 0.8.7 | PASS |
| FK/UNIQUE/CHECK/index/ON DELETE | Phase 2 schema | PostgreSQL integration/model metadata and lifecycle regression | Constraints and HNSW/partial index verified | PASS |
| Schedule overlap/race | ScheduleService | Real PostgreSQL advisory-lock concurrent tests; adjacent ranges | Only valid schedule commits; adjacent accepted | PASS |
| Concurrent booking | AppointmentService | Five concurrent PostgreSQL sessions target one slot | One success, remaining conflicts; slot consistent | PASS |
| Appointment transitions | AppointmentService | CONFIRMED → CANCELLED/COMPLETED/NO_SHOW; invalid transition and rollback tests | Expected states/timestamps and slot behavior | PASS |
| MedicalRecord lifecycle | MedicalRecordService | COMPLETED success; CONFIRMED/CANCELLED/NO_SHOW reject; duplicate and no DELETE | Appointment 1:0..1 enforced | PASS |
| MedicalRecord RBAC/privacy | Auth + MedicalRecord | Doctor ownership; Patient own-read/no update; Staff/Admin denied; audit scan | Clinical text absent from audit | PASS |
| MedicalRecord AI isolation | Documents/RAG/Tools/Risk/Voice | Recursive source/tool-name assertions and full regression | No corpus/tool/context/log dependency | PASS |
| Register/login/logout | Auth | Real PostgreSQL auth integration | Unique email, required phone, Argon2, active user, logout | PASS |
| JWT/refresh security | Auth | Expiry, rotation, revocation, reuse/family revocation | Cookie session lifecycle correct | PASS |
| CSRF/Origin/CORS/DEV boundary | Auth/Core | Missing/wrong CSRF, exact Origin, production config, expired JWT/no DEV fallback | 401/403 and startup guards correct | PASS |
| Brute-force/resource protection | Core/rate limit | Unit + HTTP 429 contract; production-disable rejection | Hashed bounded limiter + Retry-After | PASS |
| Safe errors/headers/secrets | Core/config | Unexpected exception test; secret filename scan; production headers | Sanitized 500; no tracked secret match | PASS |
| Document governance | DocumentService | APPROVED/PENDING/REJECTED; re-ingest, rollback, checksum/path/type | Only approved sources ingested | PASS |
| JSON dataset mapping | Loaders | Valid/malformed/missing/Unicode; positive/negative/anchor/article metadata | Negative excluded; anchor metadata-only | PASS |
| CSV/PDF/DOCX | Loaders | UTF-8/malformed CSV; text/no-text/invalid PDF; headings/Unicode/invalid DOCX | Supported scope works; OCR out of scope | PASS |
| Large-file resource safety | Ingestion | Source review + fixture tests | ijson streaming, batched embedding, progress, failure status/rollback | PASS review |
| BGE-M3 | Embeddings | Batch/empty/failure/dimension; real Phase 8/12 runtime | Normalized VECTOR(1024) | PASS |
| Exact/HNSW/V2/V3 | RAG | Phase 12 plan/strategy/fallback benchmark regression | Final HNSW; exact fallback; V2/V3 retained | PASS |
| Natural Vietnamese retrieval | RAG live corpus | Three real queries on 209 chunks | Two relevant; “chóng mặt” mixed/overbroad | PASS with known limitation |
| Gemini/failure isolation | Gemini/Chat | Provider matrix, invalid response, timeout, no-context | Business APIs remain available | PASS |
| Tool Calling/AI booking | Tool Layer | Selection/args/spoof/timeout/service/confirmation/conflict/repeat | Business services reused; no pre-confirm booking | PASS |
| Risk Alert | Risk/Handoff | Positive/negative/negation/educational/boundary tests | Rule-first warning; no diagnosis | PASS |
| Handoff REST/WebSocket | Handoff | State/auth/persistence/event/disconnect/reconnect/failure | PostgreSQL/REST remains authoritative | PASS |
| Voice/TTS | Voice/Frontend | Upload validation, cleanup, mocked Browser APIs, transcript-to-chat/TTS fallback | Functional pipeline; STT quality remains limited | PASS functionality / KNOWN ISSUE quality |
| Frontend UI regression | React/Vitest | Seven files, 37 tests; loading/error/empty/auth/role/business/AI/Voice | 37/37 | PASS |
| Browser E2E smoke | Playwright/Edge | Health, public discovery, protected redirect, storage boundary, validation | 3/3 | PASS scoped smoke |
| Frontend production bundle | Vite | Build before/after lazy routes | 878,33 kB → 398,03 kB largest chunk | PASS optimized |
| Dependency security | Python/npm | `pip-audit`, `pip check`, `npm audit` | Zero known vulnerabilities; no broken Python requirements | PASS |
| Full dataset claim | RAG data | File and corpus inventory | Full file absent; large subset 900.991 bytes, 400 raw/199 unique | PASS truthful status |

## Coverage notes

- Backend full regression uses PostgreSQL thật with `RUN_DB_INTEGRATION=1`.
- Automated tests mock Gemini and Browser APIs so they are repeatable and do not consume provider quota or require a microphone.
- Playwright is a scoped release smoke, not a claim that all multi-role, Gemini, WebSocket and microphone scenarios are browser-automated.
- Historical live Business MVP, Gemini, microphone and Voice evidence remains in the corresponding Phase reports.
