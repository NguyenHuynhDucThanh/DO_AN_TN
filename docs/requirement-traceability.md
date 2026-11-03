# Truy vết yêu cầu triển khai

Baseline hiện hành: SRS v1.1 Final ngày 19/10/2026. Bản v1.0 được giữ trong `docs/backups/`; đề cương đã nộp và roadmap chính thức được giữ nguyên. Tài liệu này đồng bộ trạng thái implementation và nghiệm thu đến Phase 14; final regression, documentation, report/demo/defense materials và release-readiness review đã hoàn thành. Ma trận tường minh 159 identifier SRS nằm trong `final-requirement-matrix.md`. Tài liệu không thay thế hoặc sửa ma trận yêu cầu trong SRS.

Quy ước trạng thái:

- **DONE**: đã hoàn thành và có kiểm chứng trong phạm vi phase ghi nhận.
- **PARTIAL**: một phần đã hoàn thành; phần còn lại được chỉ rõ theo roadmap.
- **TEMPORARY**: nền tảng tạm phục vụ development/test, không phải implementation production.
- **DEFERRED**: đúng chủ đích chưa triển khai vì thuộc phase sau.

## Ma trận tổng hợp đến Phase 14

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| NFR-COMP-01 | Phase 1 | Windows 11, Python 3.12; Backend và Frontend là hai project độc lập | Runtime, Uvicorn, Vite và script setup đã được kiểm tra | DONE |
| NFR-MNT-01 | Phase 1, 3–13 | Backend Modular Monolith; Frontend feature-based; Phase 13 harden cross-cutting security và lazy-load feature routes, không viết lại business/AI architecture | Backend 160/160; Frontend 37/37; Playwright 3/3; duplicate/source/privacy audit | DONE implementation Phase 13 |
| NFR-MNT-02 | Phase 1, 2, 8 | Alembic đọc URL từ cấu hình; migration nối tiếp đến `0004_add_json_document_type`; không sửa 0001–0003 | `alembic current`, `heads`, `check`; model/migration parity | DONE; 0004 là schema change thật để hỗ trợ JSON |
| NFR-SEC-02, NFR-SEC-03, NFR-SEC-04 | Phase 1 nền tảng; Phase 5 auth; Phase 7 AI secret; Phase 13–14 hardening | JWT/cookie/CSRF/RBAC giữ nguyên; secrets Backend-only; rate limit, sanitized 500, security headers, dependency/secret audit; production config guards; Phase 14 cập nhật `follow-redirects` | Auth/object-level integration; 429/headers/error tests; `pip-audit` sạch; npm production audit 0; no Critical/High open; secret scan | DONE; 12 Moderate chỉ ở dev ESLint/minimatch được chấp nhận |
| FR-AUTH-01..06, RBAC | Phase 2 schema; Phase 3 nền tảng tạm; Phase 5 production implementation | Register/login/logout/refresh/current-user/profile; `ActorContext` được giữ nguyên; JWT/session dependency đọc role active từ PostgreSQL; `X-Dev-User-Id` chỉ còn tùy chọn development/test và bị vô hiệu trong production | `test_phase3_auth.py`; `test_phase5_auth_integration.py`; Frontend auth/route tests; browser login/logout bằng cookie thật | DONE Phase 5; không viết lại business services |
| FR-CHAT-01..05, AC-AI-01 | Phase 7 | Text request đi Frontend → FastAPI → ChatService → async GeminiClient; history tối đa 10 message chỉ ở UI/request; safety baseline và controlled failure | 21 Backend mock tests; 4 Frontend tests; full regression PASS; real Gemini model/generation smoke PASS | DONE Phase 7 |
| FR-CHAT-04, NFR-REL-01/02 | Phase 6 baseline; Phase 7 | Timeout/network/400/401/403/404/429/5xx/invalid response được map an toàn; Gemini không là dependency của Business MVP | Provider-error matrix; health vẫn 200 khi chat 503; Phase 1-6 regression 75/75 | DONE implementation |
| FR-CHAT-02/03, NFR-AI-01/02 | Phase 7 baseline; Phase 10 mở rộng | System instruction không chẩn đoán/kê đơn/điều trị/giả bác sĩ; nêu giới hạn và khuyến nghị gặp nhân viên y tế | Safety instruction assertions và safe-fallback tests | DONE baseline Phase 7; Risk Alert rule-based DONE Phase 10 |
| FR-SPE-01..03 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend | Specialty list/detail/create/update/status; public UI và Admin management | Backend CRUD/conflict/rollback; RTL Specialty list/loading/empty/error | DONE Backend + Frontend |
| FR-DOC-01..03 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend | Doctor list/detail/filter Specialty/create/update; public UI và Admin master data | Backend CRUD/filter; RTL Doctor filtering | DONE Backend + Frontend |
| FR-SCH-01..05, BR-05..07 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend; Phase 6 audit | Time/range validation, advisory transaction lock theo Doctor, overlap query, slot generation, block/unblock; UI xem lịch và slot khả dụng | Phase 2 constraints; Phase 3 overlap/slot/block; Phase 4 available-slot; Phase 6 hai transaction chồng lấn và adjacent-range test | DONE; race condition đã được kiểm chứng với PostgreSQL thật |
| FR-APT-01..08, BR-08..13 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend; Phase 6 audit/E2E | `uq_appointments_occupied_slot` giữ slot cho `CONFIRMED`, `COMPLETED`, `NO_SHOW`; booking dùng `SELECT ... FOR UPDATE`; cancel/rebook/outcome; Patient và Doctor UI | 5 concurrent booking chỉ 1 success; 4 conflict 409; transition/slot consistency; cancellation boundary; API và live browser E2E | DONE Business MVP; service Phase 3 được reuse |
| FR-MR-01..06, BR-21..24, UC-12/13, NFR-PRIV-02, NFR-DATA-03, NFR-TEST-02, AC-MR-01..04 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend; Phase 5 auth/RBAC; Phase 6 E2E | Appointment 1:0..1 MedicalRecord; completed-only; Doctor ownership; Patient own-read; Staff/Admin không mặc nhiên đọc; create/get/update/history; audit metadata; không DELETE; Doctor form và Patient read-only UI | Phase 6 authenticated E2E kiểm tra invalid state, wrong doctor, duplicate, update, privacy và audit; live UI Patient → Doctor → Patient | DONE Business MVP; không viết lại service |
| FR-DOCS-01..06 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend; Phase 8 ingestion | Existing metadata/review được reuse; JSON/CSV/PDF/DOCX loader, APPROVED-only deterministic ingest, re-ingest/rollback và source traceability được thêm vào cùng module | Governance/re-ingest/failure/security tests; official subset ingest | DONE phạm vi RAG V1; full corpus là explicit operation |
| FR-RAG-01..04, NFR-DATA-02 | Phase 2 schema; Phase 8 V1; Phase 12 advanced | BGE-M3 1024, PostgreSQL/pgvector; exact baseline, HNSW Dense, BM25 + RRF và BGE reranker qua cùng RAGService; source/no-context giữ nguyên | 50-query benchmark cùng corpus/Top-K; exact và HNSW plan; Hit@5/Recall@5/MRR/latency; source và MedicalRecord isolation | DONE RAG V1 + Phase 12 experiments; final `hnsw_dense` |
| FR-TOOL-01..07, UC-06/07, AC-AI-04/05 | Phase 9 | Gemini structured function calls; strict Tool Layer gọi Specialty/Doctor/Schedule/Appointment services; identity từ ActorContext; signed explicit booking confirmation và UI button | Tool schema/selection/validation/spoofing/timeout tests; PostgreSQL booking confirmation; Gemini read-only tool smoke; Frontend confirmation/409 tests | DONE Phase 9 |
| FR-CHAT-06, NFR-AI-04, UC-11, AC-AI-07 | Phase 10 | RiskAlertService rule-based chạy trước RAG/Gemini; fixed warning; urgent handoff qua HandoffService; không chẩn đoán | 7 positive groups; negative/negation/educational cases; risk-first/failure/UI/PostgreSQL tests | DONE Phase 10 |
| FR-HO-01..04, UC-08, AC-AI-06, AC-AI-08, NFR-RT-01 | Phase 3/4 REST; Phase 9 Tool; Phase 11 WebSocket | Tool/Risk gọi lại HandoffService; authenticated Staff/Admin WebSocket phát metadata sau commit; PostgreSQL/REST authoritative và reload sau reconnect | Handoff delegation/identity; WebSocket auth/role/event/failure/reconnect; full workflow regression | DONE REST + Tool + WebSocket Phase 11 |
| FR-VOICE-01..06, UC-09/10, AC-VOICE-01..03, BR-13/19, NFR-USAB-02, NFR-COMP-01 | Phase 11 | Browser getUserMedia + MediaRecorder push-to-talk; authenticated faster-whisper Vietnamese STT; transcript vào chat pipeline hiện có; browser SpeechSynthesis TTS và text fallback | Audio validation/cleanup/STT; Browser API success/failure/TTS; transcript→existing chat tests | DONE Phase 11; SSE optional không triển khai |
| NFR-AUD-01 | Phase 2 schema; Phase 3 Backend | AuditLog metadata-only; MedicalRecord create/update không ghi nội dung lâm sàng vào audit | Seed/audit schema check và Phase 3 privacy/audit test | DONE cho nghiệp vụ Phase 3 hiện có |
| NFR-USAB-01/02 | Phase 1 foundation; Phase 4–13 Frontend | Loading/error/empty/success; AI/Voice/realtime UX; Phase 13 lazy route loading giảm initial chunk | 37/37, lint/build; largest chunk 878,33 → 398,03 kB; Playwright 3/3 | DONE Phase 13 |
| NFR-TEST-01/02 | Phase 1–14 | PostgreSQL concurrency/integration; Auth/AI/Voice/WebSocket/RAG/security/failure/privacy; browser smoke; final requirement coverage | Backend 160/160 với DB thật; Frontend 37/37; Playwright 3/3; SRS identifiers 159/159 | DONE Phase 14 |

## Chi tiết Phase 2 Final Audit

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-SCH-01..03, BR-05..07 | Phase 2 schema; Phase 3 service; Phase 6 verification | Phase 2 tạo DoctorSchedule/ScheduleSlot và constraints. Phase 3 đã thêm advisory transaction lock theo Doctor và overlap checking trong service | `test_phase2_models.py`; Phase 3 schedule validation/overlap/slot; Phase 6 PostgreSQL race/adjacent tests | SCHEMA + BACKEND + CONCURRENCY VERIFICATION DONE |
| FR-APT-01..05, BR-08..13 | Phase 2 schema; Phase 3 service | Migration 0003 và model dùng partial unique index `uq_appointments_occupied_slot` cho `CONFIRMED`, `COMPLETED`, `NO_SHOW`; Phase 3 thêm transaction booking/cancel/rebook | Test partial-index metadata, terminal status giữ slot, CANCELLED cho rebook và lifecycle service | SCHEMA DONE + BACKEND DONE |
| FR-MR-01..06, BR-21..24 | Phase 2 schema; Phase 3 Backend; Phase 4 Frontend; Phase 5 auth; Phase 6 E2E | FK + UNIQUE bảo đảm Appointment 1:0..1 MedicalRecord; Phase 3 hoàn thiện service/privacy; Phase 4 hoàn thiện UI; Phase 5 đưa actor từ JWT/session thật vào service hiện có; Phase 6 kiểm chứng toàn luồng | FK/UNIQUE/rollback; MedicalRecord suite; form/read-only; auth privacy; authenticated API và live browser E2E | DONE Business MVP |
| FR-DOCS-01..06, FR-RAG-01..04 | Phase 2 schema; Phase 3/4 metadata; Phase 8 RAG; Phase 12 experiments | Existing Documents/DocumentChunks/ingestion được reuse; Phase 12 mở rộng strategy và large controlled benchmark, không tạo corpus store thứ hai | Schema/vector + governance/loader; 400 raw/199 unique chunks; 50-query exact/HNSW/V2/V3 benchmark | DONE RAG V1 + Phase 12 advanced retrieval |
| FR-HO-01..04 | Phase 2 schema; Phase 3/4 REST; Phase 11 WebSocket | HandoffRequest schema/status giữ nguyên; Phase 11 mở rộng workflow hiện có bằng authenticated metadata notification/status | Schema/workflow regression; WebSocket auth/event/reconnect/failure tests | DONE REST + WebSocket Phase 11 |

## Chi tiết Phase 3

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| NFR-MNT-01 | Phase 3 | Router → Service → Repository → SQLAlchemy → PostgreSQL cho các module nghiệp vụ | Full Backend suite với PostgreSQL integration | DONE |
| FR-SPE-01..03; FR-DOC-01..03 | Phase 3 | Specialty và Doctor CRUD/filter theo quyền tạm | CRUD/filter/conflict/rollback tests | DONE Backend |
| FR-SCH-01..05; FR-APT-01..08 | Phase 3 implementation; Phase 6 verification | Schedule overlap lock, slot generation/blocking, booking lock, cancel/rebook và COMPLETED/NO_SHOW | Phase 3 service tests; Phase 6 true-concurrency, race, transition, boundary và E2E tests | DONE Backend + Business MVP verification |
| FR-MR-01..06, BR-21..24 | Phase 3; Phase 5 auth integration; Phase 6 E2E | `MedicalRecordService` create/get/update/history; completed-only, ownership, Patient own-read, audit và không hard-delete; service được giữ nguyên qua Phase 5/6 | Creation, duplicate 409, invalid state, update, unauthorized actor, history, rollback/audit privacy; real-auth API và live UI E2E | DONE Backend + auth + Business MVP E2E |
| FR-DOCS-01..06 | Phase 3 metadata; Phase 8 ingestion | Document metadata CRUD/Admin review được giữ nguyên; Phase 8 mở rộng service/router hiện có | Metadata/review regression + Phase 8 ingestion suite | DONE RAG V1 |
| FR-HO-01..04 | Phase 3 REST; Phase 11 WebSocket | Handoff REST ticket, assignment/state transition được reuse; Phase 11 thêm notification/status sau commit | Handoff workflow + Phase 11 realtime tests | DONE REST + WebSocket |
| FR-AUTH-01..06, RBAC | Phase 3 nền tảng tạm; Phase 5 hoàn thiện | `ActorContext` ban đầu nhận DEV identity; Phase 5 giữ interface và cấp actor từ JWT/session, role thật từ DB; production chặn DEV auth | 401 thiếu actor, role DB, 403 clinical data và Phase 5 auth integration suite | DONE Phase 5 |

## Chi tiết Phase 4

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| Toàn bộ API nghiệp vụ Phase 3 | Phase 4 reuse | Frontend gọi lại 37 OpenAPI operations; không sửa hoặc sao chép business logic Backend | Backend regression 38/38 PASS; không có migration mới, `alembic check` sạch | REUSED |
| FR-SPE-01..03; FR-DOC-01..03 | Phase 4 | Public list/detail/filter và Admin management | RTL Specialty list và Doctor filter | DONE Frontend |
| FR-SCH-04; FR-APT-01..08 | Phase 4 | Tìm slot, booking, 409 conflict, list/cancel và Doctor outcome | RTL available slots, booking/409, cancel và outcome | DONE Frontend |
| FR-MR-01..06, UC-12/13 | Phase 4; Phase 5 auth integration | Doctor create/update form; Patient history/detail read-only; không có clinical route cho Staff/Admin; role route dùng session thật | RTL form đủ bốn field, Patient history read-only và Phase 5 role-route test | DONE Frontend + auth integration |
| FR-DOCS-01..06 | Phase 4 metadata UI; Phase 8 RAG UI | Document metadata/status/review UI được giữ; Chat UI thêm source traceability/error/retry | Frontend 25/25, lint/build | DONE Phase 8 UI |
| FR-HO-01..04 | Phase 4 REST UI; Phase 11 realtime UI | Handoff create/list/state UI được reuse; Staff/Admin nhận event và reload REST sau connect/reconnect | Frontend REST regression + Phase 11 reconnect/event tests | DONE REST + realtime UI |
| NFR-USAB-01 | Phase 4 | Loading/error/empty/success và safe API message | Vitest/RTL state/error tests; mobile/browser check | DONE |
| Phase 5 boundary | Phase 4 temporary → Phase 5 replaced | Session JWT/refresh cookie đã thay cơ chế DEV mặc định; DEV actor chỉ xuất hiện khi bật cờ development, không fallback sau JWT lỗi và bị chặn trong production | Backend production-guard/expired-JWT tests; Frontend auth tests; browser login/logout thật | DONE Phase 5 |

## Chi tiết Phase 5

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-AUTH-01, DR-04 | Phase 5 | Patient register với email duy nhất, password, full_name, phone bắt buộc; password lưu Argon2 hash | Register, missing phone, duplicate email, hash/not-plaintext tests | DONE |
| FR-AUTH-02, UC-01 | Phase 5 | Login email case-insensitive, password verification và ACTIVE-user check | Invalid password, mixed-case email, inactive-user tests | DONE |
| FR-AUTH-03 | Phase 5 | Logout revoke refresh session và xóa auth/CSRF cookies | Logout, revoked-session và cookie-clearing tests | DONE |
| FR-AUTH-04 | Phase 5 | Opaque refresh token; DB chỉ lưu SHA-256 hash; rotation, replacement chain, family revocation khi reuse | Rotation/hash/replaced-session/reuse-family tests | DONE |
| FR-AUTH-05..06 | Phase 5 | Current session user và cập nhật profile; Patient không được xóa phone bắt buộc | `/auth/me`, profile update và Patient-phone invariant tests | DONE |
| RBAC, BR-06 | Phase 5 | JWT/session → auth dependency → ActorContext; active roles đọc từ DB; Backend vẫn authoritative ở role/object level | 401/403, role-route và protected-route tests | DONE |
| BR-22, NFR-PRIV-02, NFR-TEST-02 | Phase 5 integration; Phase 6 E2E | MedicalRecord service Phase 3 được reuse; Patient own-read, Doctor ownership, Staff/Admin không có clinical-read mặc định | MedicalRecord privacy test bằng cookie/JWT thật; Phase 6 API/live UI E2E | DONE |
| NFR-SEC-02..04 | Phase 5 | Short-lived JWT, HttpOnly cookies, CSRF token/header, exact Origin/CORS, refresh revocation/reuse, production configuration guard | Backend security-boundary tests và browser login/logout; không lưu token/password trong localStorage | DONE phạm vi Phase 5 |
| NFR-USAB-01 | Phase 5 | Login/Register/Logout, restore session, ProtectedRoute, RoleRoute và UX 401/403 | 7 auth-focused Frontend tests; tổng 19/19 PASS | DONE |
| NFR-MNT-01 | Phase 5 | Auth bổ sung qua router/service/repository/dependency; không sao chép business logic hoặc sửa service signature | Full regression 46/46 Backend và 19/19 Frontend | DONE |

## Chi tiết Phase 6

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-SCH-01..05, BR-05..07 | Phase 3 reuse; Phase 6 verification | `ScheduleService` và advisory transaction lock theo Doctor được giữ nguyên | Hai PostgreSQL session đồng thời tạo `08:00–10:00` và `09:00–11:00`: 1 success + 1 conflict; `08:00–10:00` và `10:00–12:00` cùng commit | DONE |
| FR-APT-01..03, BR-08..10, NFR-DATA-03 | Phase 3 reuse; Phase 6 verification | `SELECT ... FOR UPDATE`, slot status và DB partial unique index phối hợp giữ invariant booking | 5 worker/session độc lập cùng booking một slot: 1 success + 4 `409 slot_unavailable`; DB có đúng 1 occupied appointment | DONE |
| FR-APT-04..08, BR-11..13 | Phase 3 reuse; Phase 6 verification | Cancel/rebook, `COMPLETED`, `NO_SHOW`, ownership và slot consistency | Test transition terminal/sai, other-Patient cancel 403, CANCELLED giải phóng slot, COMPLETED/NO_SHOW giữ BOOKED | DONE |
| BR-12 | Phase 6 verification | Patient chỉ hủy Appointment `CONFIRMED` của mình khi `now < slot.start_at`; không có buffer khác | Freeze clock tại `slot.start_at` bị từ chối; trước một microsecond thì hợp lệ | DONE |
| FR-MR-01..06, BR-21..24, UC-12/13 | Phase 3–5 reuse; Phase 6 E2E | Booking → COMPLETED → Doctor create/update MedicalRecord → Patient history/read-only; privacy và audit giữ nguyên | Authenticated API E2E kiểm tra 409/403/duplicate/privacy/audit; live browser E2E trên Backend/PostgreSQL thật | DONE |
| UC-01..07, NFR-USAB-01 | Phase 4/5 reuse; Phase 6 live E2E | Frontend Phase 4 + Auth Phase 5 chạy toàn luồng Business MVP không AI | Patient login/book/cancel/rebook; Doctor login/complete/create record; Patient xem record; console 0 error/warning | DONE |
| NFR-TEST-01/02 | Phase 6 | Thêm 5 PostgreSQL integration tests, không lặp lại service implementation | Full regression Backend 51/51; Frontend 19/19; lint/build PASS | DONE |

## Chi tiết Phase 7

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-CHAT-01, AC-AI-01 | Phase 7 | `/api/v1/chat/messages`, `ChatService`, async `GeminiClient`, React `/chat` | Stable contract, API validation, UI send/render/history tests và real API smoke | DONE |
| FR-CHAT-02/03, NFR-AI-01/02 | Phase 7 baseline | Safety instruction, giới hạn y tế và safe fallback | Safety content và fallback assertions | DONE baseline |
| FR-CHAT-04, NFR-REL-01/02 | Phase 7 | Provider failure isolation; AI config optional khi Backend startup | Timeout/network/status/invalid-response matrix; health 200 khi chat 503 | DONE |
| FR-CHAT-05 | Phase 7 | Tối đa 10 message trong React state/request; không persistence | Frontend second-turn history test; Pydantic history bound | DONE scope Phase 7 |
| NFR-SEC-02/04, NFR-PRIV-02 | Phase 7 | Key Backend-only; không log prompt/response; không import/query MedicalRecord | Secret repr, source dependency isolation và payload-only tests | DONE implementation |
| Phase boundary | Phase 7 | `tools=None`, automatic function calling disabled; không RAG/Voice/Risk Alert/AI booking | Source/config assertions và UI absence checks | DONE |
| Model availability | Phase 7 acceptance | `GEMINI_MODEL` configurable; `scripts/check_gemini.py` kiểm tra model + generation thật | PASS ngày 23/10/2026; key/model được nạp nhưng giá trị bí mật không bị in | DONE; Phase 7 PASS |

## Chi tiết Phase 8

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-DOCS-01..06 | Phase 3/4 reuse; Phase 8 extend | APPROVED-only JSON/CSV/PDF/DOCX ingestion trong Document module hiện có; normalization, dedup, chunking, deterministic re-ingest | Loader fixtures, governance, rollback, traversal/type/size guards và official subset ingestion | DONE RAG V1 |
| FR-RAG-01/02, NFR-DATA-02 | Phase 8 | Một BGE-M3 service; batch normalized vector 1024; existing DocumentChunk/pgvector | Real BGE CPU smoke; dimension/batch/failure tests; 10 embedded smoke chunks | DONE |
| FR-RAG-03 | Phase 8 | Exact cosine Top-K chỉ trên APPROVED+COMPLETED; threshold configurable; HNSW bị tắt cục bộ cho baseline | PostgreSQL ranking/approved-only/source tests; EXPLAIN không dùng HNSW | DONE exact V1 |
| FR-RAG-04, FR-CHAT-01..04 | Phase 8 reuse/extend | ChatService/GeminiClient hiện có nhận retrieved context; system/question/context tách biệt; answer + sources; no-context fallback | Prompt injection assertion, sources/no-context/retrieval/provider failure tests và real grounded smoke | DONE RAG V1 |
| NFR-PRIV-02, BR-23 | Phase 8 | Không có đường MedicalRecord → Document/DocumentChunk/embedding/retrieval/Gemini context | Source dependency scan + full privacy regression | DONE hard isolation |
| NFR-TEST-01/02 | Phase 8 | Fixed evaluation set gồm 4 anchor thật; Recall@K, Hit@K, MRR repeatable | Recall@5 1,0000; Hit@5 1,0000; MRR 0,8750 trên official smoke subset | DONE baseline; không suy rộng full corpus |
| Phase boundary | Phase 8 | Không Tool Calling/AI booking/BM25/RRF/reranker/Voice/WebSocket/full Risk Alert | Source/UI assertions và architecture audit | DONE; Phase 9 chưa bắt đầu |

## Chi tiết Phase 9

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-TOOL-01 | Phase 9 | `search_specialty(query)` gọi `SpecialtyService.search`; chỉ trả Specialty ACTIVE có thật | Service delegation, empty-result và real Gemini tool-selection smoke | DONE |
| FR-TOOL-02 | Phase 9 | `list_doctors(specialty_id, filters)` gọi `DoctorService.list` | Strict structured arguments và service adapter tests | DONE |
| FR-TOOL-03 | Phase 9 | `available_slots(doctor_id, date)` gọi `ScheduleService.available_slots`; ngày được quy đổi UTC+07 | Argument/date validation, relationship serialization và regression | DONE |
| FR-TOOL-04/05, BR-08 | Phase 9 | Pydantic `extra=forbid`; tool schema không nhận identity; ActorContext do auth dependency cấp; Gemini không chạm SQL/ORM | Missing/malformed/unknown/fake identity/role spoofing/unauthorized/no-direct-ORM tests | DONE |
| FR-TOOL-06, UC-07, AC-AI-04/05 | Phase 9 | `create_booking` chỉ sinh signed `CONFIRMATION_REQUIRED`; endpoint riêng sau button mới gọi existing AppointmentService | No-booking-before-confirm, actor mismatch, PostgreSQL success, repeated/409 và Frontend confirmation tests | DONE |
| FR-TOOL-07 | Phase 9 | Booking thật reuse lock/state/index/transaction của AppointmentService Phase 3/6 | Real DB confirmation test + full Phase 6 concurrency regression | DONE; service REUSED |
| FR-HO-01..04, UC-08, AC-AI-06 | Phase 9 Tool; Phase 11 WebSocket | `handoff_to_staff` gọi existing HandoffService; Phase 11 phát event metadata sau commit bằng cùng realtime layer | Delegation/identity/source + WebSocket event/failure/reconnect tests | DONE Tool/REST/WebSocket |
| FR-RAG-01..04 | Phase 8 reuse trong Phase 9 | Static knowledge vẫn qua RAG; dynamic Doctor/Slot không qua corpus | RAG regression và source-isolation tests | DONE V1; REUSED |
| NFR-PRIV-02, BR-23 | Phase 9 | Registry/Tool Layer không có MedicalRecord function/import/context | Registry/source scan và full privacy regression | DONE hard isolation |

## Chi tiết Phase 10

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-CHAT-01..05, NFR-AI-01/02 | Phase 7–10 reuse/extend | Một ChatOrchestrator phân route risk/knowledge/business/booking/handoff; safety prompt/fallback cũ được giữ | Route unit tests và full regression | DONE AI MVP |
| FR-CHAT-06, DR-07 | Phase 10 | Pure `RiskAlertService` chạy trước Gemini với 7 nhóm rule demo, Unicode normalization, negation và educational guards | Positive/negative/false-positive fixed cases | DONE |
| NFR-AI-04, UC-11, AC-AI-07 | Phase 10 | Fixed non-diagnostic urgent warning; recommended actions; handoff PENDING/FAILED; Gemini không được gọi khi trigger | Risk-first, no-diagnosis, handoff failure và Frontend alert tests | DONE |
| FR-RAG-01..04, AC-AI-02/03 | Phase 8 reuse; Phase 10 routing | Knowledge route gọi lại RAG V1 và giữ source traceability; empty retrieval fixed fallback | knowledge→RAG/source, empty/failure regression | DONE V1; REUSED |
| FR-TOOL-01..07, AC-AI-04/05 | Phase 9 reuse; Phase 10 routing | Dynamic business route bỏ qua corpus, dùng Gemini function call + ToolExecutor; booking confirmation giữ nguyên | Doctor/slot tool, confirmation, conflict regression | DONE; REUSED |
| FR-HO-01..03, AC-AI-06/08 | Phase 3 reuse; Phase 10 Risk Handoff; Phase 11 WebSocket | Risk Alert tạo URGENT/PENDING qua HandoffService; sau commit dùng cùng metadata notification cho Staff/Admin | PostgreSQL persistence/priority/privacy + WebSocket event/reconnect tests | DONE REST + Risk + WebSocket |
| NFR-PRIV-02, BR-23 | Phase 10 | Risk engine không query MedicalRecord; AI source không import MedicalRecord | Recursive source isolation + privacy regression | DONE hard isolation |
| AC-BIZ-06, FR-CHAT-04 | Phase 6–10 | AI/RAG/Tool failure không làm mất API/UI nghiệp vụ thủ công | Controlled failure tests và Business MVP regression | DONE |

## Chi tiết Phase 11

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-HO-03, NFR-RT-01, AC-AI-08 | Phase 11 | `WS /api/v1/handoffs/ws`; Staff/Admin auth từ cookie/JWT + role DB; `handoff.created/updated` sau commit; payload metadata-only | Authenticated/401/403; event metadata; socket failure; Frontend reconnect + REST invalidation | DONE |
| FR-HO-01/02, UC-08/11 | Phase 3/9/10 reuse; Phase 11 extend | Existing HandoffService/model/REST/UI được giữ; User/Tool/Risk ticket dùng cùng realtime publisher | Handoff REST/tool/risk regression và full PostgreSQL suite | DONE; REUSED/EXTENDED |
| FR-VOICE-01/05, UC-09, AC-VOICE-01 | Phase 11 | Browser `getUserMedia` + `MediaRecorder`, push-to-talk, track cleanup; authenticated multipart STT endpoint | Success, denied, unavailable, unsupported; Blob upload; empty/type/size/STT failure/cleanup | DONE |
| FR-VOICE-02, BR-13, AC-VOICE-02 | Phase 11 | Transcript đi vào form và request của ChatPage/ChatOrchestrator hiện có | Transcript→`sendChatMessage`; full AI regression | DONE; chatbot logic REUSED |
| FR-VOICE-03/04, UC-10, AC-VOICE-03 | Phase 11 | Browser SpeechSynthesis ưu tiên voice Việt, play/stop; text luôn là output chính | TTS play/stop và unavailable/text fallback | DONE |
| FR-VOICE-06 | Phase 11 optional | Không thêm SSE vì text streaming không phải điều kiện MVP và sẽ tăng complexity không cần thiết | Architecture audit | NOT REQUIRED |
| NFR-PRIV-02, BR-23 | Phase 11 | Audio tạm xóa trong `finally`; không Gemini audio; WebSocket không reason/clinical content; không có MedicalRecord import/context | Cleanup/privacy payload/source audit + full MedicalRecord regression | DONE hard isolation |
| NFR-REL-01, NFR-USAB-02 | Phase 11 | Voice/WebSocket failure không phá text chat, Handoff REST hoặc Business MVP; reconnect reload REST | Frontend failure/reconnect tests; Backend 144/144, Frontend 37/37 | DONE |

## Chi tiết Phase 12

| Requirement | Phase thực tế | Implementation | Test / kiểm chứng | Status |
| --- | --- | --- | --- | --- |
| FR-DOCS-01..06 | Phase 8 reuse; Phase 12 corpus | Downloader/Document approval/ingestion hiện có được reuse; deterministic range `[0,400)` tạo 199 unique chunks sau normalize/dedup | 400 raw, 199 unique contents, 201 duplicate removed, 199 embedded; 140,286 giây | DONE large controlled subset; không phải full dataset |
| FR-RAG-01/02, NFR-DATA-02 | Phase 8 reuse; Phase 12 extend | Một BGE-M3 service, một DocumentChunk/pgvector store và strategy factory tập trung | Cùng 209 DB chunks, 50 query, BGE-M3 1024, Top-K=5 cho mọi strategy | DONE; REUSED/EXTENDED |
| FR-RAG-03 | Phase 8 exact; Phase 12 HNSW | Exact baseline giữ `enable_indexscan=off`; HNSW dùng index cosine hiện có với `ef_search=40` | EXPLAIN exact và HNSW plan PASS; cả hai Hit/Recall@5 0,96, MRR 0,8447 | DONE |
| FR-RAG-03 | Phase 12 V2 | Unicode NFC/casefold BM25 cùng corpus + HNSW dense candidates, deterministic RRF (`20+20`, `rrf_k=60`) | Unicode/empty/ranking/dense-only/sparse-only/overlap/determinism; Hit/Recall@5 0,96, MRR 0,7713 | DONE experiment |
| FR-RAG-03 | Phase 12 V3 | V2 candidates → `BAAI/bge-reranker-v2-m3` CPU → Top-K=5; không rerank toàn corpus | Ordering/Top-K/empty/model failure; Hit/Recall@5 0,98, MRR 0,8463; median 8.221,624 ms | DONE experiment; không chọn production vì latency |
| FR-RAG-04, FR-CHAT-01..04 | Phase 8–10 reuse; Phase 12 strategy selection | Chat/RAG pipeline và source response giữ nguyên; `RAG_STRATEGY=hnsw_dense` là final config; production fallback exact | Factory/fallback/source tests; AI regression trong full Backend 152/152 | DONE; final HNSW Dense |
| NFR-PRIV-02, BR-23 | Phase 12 | MedicalRecord không nằm trong Dense/BM25/reranker/evaluation/Gemini context | Source/dependency audit và full privacy regression | DONE hard isolation |
| NFR-TEST-01/02 | Phase 12 | Fixed 50-query grounded evaluation; Hit@K/Recall@K/MRR và mean/median/p95 latency; JSON/CSV evidence | Backend 152/152 DB integration; Frontend 37/37; lint/build/compile/pip check PASS | DONE |

## Tóm tắt roadmap đến Phase 14

- Phase 5 đã giữ `ActorContext` và toàn bộ business services, đồng thời thay authentication dependency bằng JWT/Refresh Token/Argon2/CSRF/RBAC thật.
- Phase 6 đã reuse nguyên `ScheduleService`, `AppointmentService` và `MedicalRecordService`; concurrency/race condition, state transition, cancellation boundary và Business MVP/MedicalRecord E2E đã PASS.
- Phase 7 Gemini Basic Chatbot đã hoàn thành implementation, automated regression và real Gemini model/generation smoke; Phase 7 PASS.
- Phase 8 đã mở rộng Document module hiện có với ingestion, chunking, BGE-M3 và exact pgvector retrieval; không tạo Document module thứ hai.
- Phase 9 đã hoàn thành Tool Calling bằng adapter gọi lại AppointmentService/HandoffService, không sao chép business logic; explicit button confirmation đã PASS.
- Phase 10 đã hoàn thành AI MVP thống nhất và Risk Alert rule-based; cảnh báo chạy trước Gemini và handoff dùng lại workflow hiện có.
- Phase 11 đã mở rộng Handoff REST workflow hiện có bằng authenticated WebSocket và bổ sung Voice input/output layer trên chatbot hiện có; không tạo module Handoff/chatbot thứ hai.
- Phase 11 Vietnamese STT live pipeline hoạt động nhưng chất lượng nhận dạng trên máy demo còn hạn chế; đây là known limitation/future improvement và không được tuning lại trong Phase 12.
- Phase 12 đã hoàn thành Exact/HNSW/V2/V3 experiments trên cùng large controlled corpus; final strategy là HNSW Dense. Large subset không được gọi là full dataset.
- Phase 13 đã hoàn thành full regression, security/dependency hardening, bundle optimization, scoped Playwright smoke và release-readiness evaluation.
- Phase 14 đã đóng codebase, đồng bộ README/traceability, tạo sơ đồ/report/demo/defense/screenshot checklist, chạy final regression và chốt READY cho phạm vi đồ án/demo có kiểm soát.
- MedicalRecord không được đưa vào RAG/Gemini, không cho Tool Calling đọc trong MVP và chỉ dùng dữ liệu demo/synthetic.

## Kết quả kiểm chứng ghi nhận trong Phase 8

| Hạng mục | Kết quả |
| --- | --- |
| Riêng Phase 6 PostgreSQL integration | 5/5 PASS |
| Phase 8 loader/RAG unit + Phase 7 chatbot regression | 37/37 PASS |
| Phase 8 PostgreSQL/pgvector integration | 6/6 PASS |
| Backend Pytest với PostgreSQL integration | 97/97 PASS |
| Frontend Vitest + React Testing Library | 25/25 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; cảnh báo chunk lớn không chặn build |
| Alembic | Head `0004_add_json_document_type`; `alembic check` không có operation mới |
| Browser + Backend/PostgreSQL thật | Patient book/cancel/rebook; Doctor COMPLETED/create MedicalRecord; Patient xem history/detail read-only; console không có error/warning |
| Dọn dữ liệu live | Schedule/slot/appointment/MedicalRecord/audit tạm đã xóa; refresh session tạm bị thu hồi; password seed trở về sentinel |
| BGE-M3 real smoke | Windows CPU PASS: 2 vector, dimension 1024, norm 1,0 |
| Dataset smoke | 44.868 byte; 20 raw; 10 unique; 10 duplicate removed; 10 chunk/embedding; 31,208 giây |
| Exact evaluation | 4 query, Top-K=5; Recall@5 1,0000; Hit@5 1,0000; MRR 0,8750; HNSW không được dùng |
| Gemini grounded smoke | PASS: answer 334 ký tự, 5 source có document id thật; không hiển thị key/nội dung nhạy cảm |

Các kết quả trên là kết quả lịch sử của Phase 8. Việc đồng bộ không thay đổi SRS hoặc roadmap; migration 0004 chỉ mở rộng file type JSON theo requirement Phase 8. Full dataset chưa được ingest và không được báo PASS giả.

## Kết quả kiểm chứng ghi nhận trong Phase 9

| Hạng mục | Kết quả |
| --- | --- |
| Backend Pytest với PostgreSQL integration | 111/111 PASS |
| Frontend Vitest + React Testing Library | 27/27 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; cảnh báo chunk lớn không chặn build |
| Alembic | `current` và `heads` đều `0004_add_json_document_type`; không tạo migration Phase 9 |
| Gemini Tool Calling smoke | PASS: chọn `search_specialty`, result `SUCCESS`, có final answer, không mutation |
| Booking confirmation real DB | PASS: chưa có Appointment trước nút; sau confirm gọi existing AppointmentService và tạo `CONFIRMED` |
| MedicalRecord isolation | PASS: không có MedicalRecord tool/import/context |

Các số liệu trên là kết quả lịch sử Phase 9.

## Kết quả kiểm chứng ghi nhận trong Phase 10

| Hạng mục | Kết quả |
| --- | --- |
| Backend Pytest với PostgreSQL integration | 136/136 PASS |
| Frontend Vitest + React Testing Library | 29/29 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; cảnh báo chunk lớn không chặn build |
| Risk rule scenarios | 7 positive groups + negative/negation/educational false-positive cases PASS |
| Risk execution order | PASS: short-circuit trước RAG/Gemini |
| Risk Handoff PostgreSQL | PASS: `RISK_ALERT`, `URGENT`, `PENDING`, không lưu raw symptom text |
| Alembic | Head `0004_add_json_document_type`; `alembic check` không có operation mới |
| OpenAPI | Version `0.10.0`; ChatResponse có `risk_alert` |
| MedicalRecord isolation | PASS: không tool/RAG/risk context/import |

Các số liệu trên là kết quả lịch sử Phase 10; Phase 11 được triển khai ở phần dưới theo yêu cầu riêng.

## Kết quả kiểm chứng ghi nhận trong Phase 11

| Hạng mục | Kết quả |
| --- | --- |
| Backend Phase 11 targeted | 8/8 PASS |
| Backend Pytest với PostgreSQL integration | 144/144 PASS |
| Frontend Phase 11 targeted | 8/8 PASS |
| Frontend Vitest + React Testing Library | 37/37 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; cảnh báo chunk lớn không chặn build |
| Dependency check | `pip check` PASS; faster-whisper và multipart cài trực tiếp trên Windows |
| Alembic | Head `0004_add_json_document_type`; `alembic check` không có operation mới |
| API | Version `0.11.0`; `POST /api/v1/voice/transcriptions`; `WS /api/v1/handoffs/ws` |
| MedicalRecord isolation | PASS: không Voice/WebSocket payload/context/import |
| Microphone hardware live | Pipeline microphone/MediaRecorder/faster-whisper đã chạy và trả transcript; chất lượng nhận dạng tiếng Việt trên máy demo còn sai lệch cao, được ghi `LIMITED / NOT PASS` cho quality tuning và chuyển future improvement |

Phase 11 không bị refactor trong Phase 12; giới hạn chất lượng STT vẫn được giữ minh bạch.

## Kết quả kiểm chứng ghi nhận trong Phase 12

| Hạng mục | Kết quả |
| --- | --- |
| Corpus | LARGE CONTROLLED SUBSET: 400 raw, 199 unique content/chunks, 201 duplicate removed, 199 embedded; ingestion 140,286 giây |
| Corpus truy vấn thực tế | 209 chunks: 199 large subset + 10 smoke chunks Phase 8; giống nhau cho mọi strategy |
| Evaluation | 50 grounded Vietnamese queries; BGE-M3 1024; Top-K=5 |
| Exact Dense | Hit/Recall@5 0,96; MRR 0,8447; mean 5,429 ms; exact plan PASS |
| HNSW Dense | Hit/Recall@5 0,96; MRR 0,8447; mean 3,987 ms; HNSW plan PASS |
| V2 BM25 + RRF | Hit/Recall@5 0,96; MRR 0,7713; mean 69,005 ms |
| V3 + BGE reranker CPU | Hit/Recall@5 0,98; MRR 0,8463; median 8.221,624 ms; resource limitation ghi rõ |
| Final retrieval | `hnsw_dense`; exact dense giữ làm baseline/fallback |
| Backend không bật integration | 111 passed, 41 skipped đúng điều kiện |
| Backend với PostgreSQL integration | 152/152 PASS |
| Frontend | 37/37 PASS; ESLint 0 warning; production build PASS |
| Alembic | `0004_add_json_document_type (head)`; không migration Phase 12 |
| Dependency/compile | `pip check` và Python compileall PASS |
| MedicalRecord isolation | PASS |

**PHASE 12: PASS — LARGE CONTROLLED CORPUS BENCHMARK PASS.**

## Chi tiết và kết quả kiểm chứng Phase 13

| Requirement / boundary | Phase thực tế | Implementation / hardening | Test / evidence | Status |
| --- | --- | --- | --- | --- |
| NFR-SEC-02/03/04, NFR-REL-01/02 | Phase 5–13 | Giữ Auth/CSRF/CORS/RBAC; thêm bounded hashed rate limiter, 429 Retry-After, sanitized 500, security headers và production guards | Phase 13 unit/HTTP tests; Auth PostgreSQL regression; secret scan | DONE |
| NFR-SEC-02 | Phase 13 | PyJWT 2.15.0, python-multipart 0.0.31, fast-uri 3.1.9 | `pip-audit`: no known vulnerabilities; `npm audit`: 0; `pip check`: PASS | DONE; Critical/High open = 0 |
| FR-APT-01..08, BR-08..13 | Phase 3/6 reuse; Phase 13 regression | Không sửa AppointmentService; kiểm chứng lock/index/state/rollback thật | 5 concurrent booking chỉ 1 success; transition/cancel/rebook suite trong 160/160 | DONE; REUSED |
| FR-MR-01..06, BR-21..24, NFR-PRIV-02 | Phase 3–6 reuse; Phase 13 extend test | COMPLETED-only; thêm explicit CONFIRMED/CANCELLED/NO_SHOW rejection; ownership/audit/no DELETE/AI isolation giữ nguyên | PostgreSQL terminal-state, duplicate, privacy, audit và source/tool-name tests | DONE |
| FR-DOCS-01..06 | Phase 8 reuse; Phase 13 hardening | Streaming JSON/batch/progress/rollback giữ nguyên; CSV không giữ `negative` trong metadata | JSON/CSV/PDF/DOCX + governance regression; new CSV negative test | DONE |
| FR-RAG-01..04 | Phase 8/12 reuse; Phase 13 evaluation | Final HNSW, exact fallback, fixed metrics giữ nguyên; natural Vietnamese live check bổ sung | Strategy/plan/full AI regression; 2/3 query relevant rõ, 1 mixed documented | DONE with known corpus limitation |
| FR-TOOL-01..07, FR-CHAT-01..06 | Phase 7–10 reuse; Phase 13 regression | Provider failure, Tool confirmation/identity/service isolation và Risk rule-first giữ nguyên | Full backend regression 160/160 | DONE |
| FR-HO-01..04, NFR-RT-01 | Phase 3/11 reuse; Phase 13 regression | REST/PostgreSQL authoritative; WebSocket notification/reconnect/failure layer giữ nguyên | Handoff REST/WebSocket regression | DONE |
| FR-VOICE-01..06, NFR-USAB-02 | Phase 11 reuse; Phase 13 regression | Browser API/STT/TTS/text fallback không rewrite | Automated Voice regression PASS; live quality vẫn LIMITED | DONE functionality; KNOWN ISSUE quality |
| NFR-USAB-01/02 | Phase 13 | React.lazy/dynamic import cho feature route, loading fallback | Largest JS 878,33 → 398,03 kB; 37/37; lint/build PASS | DONE optimized |
| NFR-TEST-01/02 | Phase 13 | Test matrix và release smoke Edge cổng riêng | Backend 160/160; Frontend 37/37; Playwright 3/3 | DONE |
| NFR-MNT-02 | Phase 13 | `check_database.py` lấy head động từ Alembic; không schema change | current/heads `0004`; check no-op; seed idempotent | DONE; no Phase 13 migration |

### Phase 13 performance and release evidence

| Hạng mục | Kết quả |
| --- | --- |
| Health REST, 50 request | mean 7,826 ms; median 2,875 ms; p95 3,628 ms |
| RAG retrieval | Giữ Phase 12 exact/HNSW/V2/V3 số liệu thật; không benchmark lại giả tạo |
| Large dataset | Full file absent; LARGE CONTROLLED SUBSET 400 raw/199 unique, corpus DB 209 chunks |
| Frontend bundle | Largest chunk giảm khoảng 54,7%; warning >500 kB biến mất |
| Playwright | 3/3 scoped live smoke; không tuyên bố full multi-role/provider/hardware E2E |
| Security | Trạng thái checkpoint Phase 13: audit sạch; Phase 14 xử lý advisory HIGH mới của `follow-redirects`; final no Critical/High open, production npm audit 0, còn 12 Moderate dev-tool-only được chấp nhận |

Known issues được chấp nhận và ghi trong `phase-13.md`: STT accuracy thấp trên máy demo; full dataset chưa ingest; query “chóng mặt” retrieval còn mixed; per-process rate limit cần edge policy khi scale; full multi-role/provider/microphone Playwright chưa automated; large ingestion nên chạy controlled script thay vì HTTP dài.

**PHASE 13: PASS — RELEASE READINESS PASS cho phạm vi đồ án/demo có kiểm soát.**

## Chi tiết và kết quả kiểm chứng Phase 14

| Hạng mục | Kết quả cuối |
| --- | --- |
| Final code/secret/dataset audit | Sửa docstring Auth stale; không phát hiện real credential; `.env`/dataset được ignore; không có full 1 GB dataset trong source |
| Dependency change | `follow-redirects` cập nhật lên 1.16.2 bằng non-breaking audit fix; Frontend regression lại toàn bộ |
| Migration | Giữ nguyên `0001 → 0002 → 0003 → 0004`; current/heads/check PASS; không có migration Phase 14 |
| Final regression | Backend 160/160; Frontend 37/37; lint/build PASS; Playwright scoped smoke 3/3 |
| Database | PostgreSQL 18.6; pgvector 0.8.7; VECTOR/cosine/Alembic check PASS; seed hai lần PASS |
| Security | `pip-audit` sạch; npm production audit 0; no Critical/High open; 12 Moderate dev ESLint/minimatch accepted |
| Requirement coverage | 159/159 SRS v1.1 identifiers xuất hiện trong final matrix |
| Documentation | README, final architecture diagrams, requirement/test/security/RAG-performance reports, demo script, defense notes và manual screenshot checklist |
| Scope honesty | full dataset chưa ingest; Voice quality limited; Playwright scoped; unmeasured latencies ghi NOT MEASURED |

**PHASE 14: PASS — FINAL RELEASE READINESS: READY cho phạm vi đồ án/demo có kiểm soát.**

Không có Phase 15 và không thêm feature mới sau khi chốt, trừ bug fix bắt buộc kèm regression.
