# Ma trận truy vết yêu cầu cuối

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

Nguồn yêu cầu: SRS v1.1 Final. Ma trận này bổ sung lớp tổng hợp cuối cho `requirement-traceability.md`; các requirement được liệt kê tường minh để kiểm tra độ phủ. `DONE` nghĩa là có implementation và bằng chứng test phù hợp. `DONE WITH LIMITATION` nghĩa là chức năng đạt acceptance nhưng còn giới hạn đã công khai. `FUTURE WORK` chỉ áp dụng cho requirement mức Could/ngoài MVP được SRS cho phép.

| Requirement | Phase | Implementation | API / UI | Test / evidence | Result |
| --- | --- | --- | --- | --- | --- |
| FR-AUTH-01, FR-AUTH-02, FR-AUTH-03, FR-AUTH-04, FR-AUTH-05, FR-AUTH-06 | 5, 13 | Argon2; access JWT; opaque refresh hash/rotation/revocation/reuse; profile rules; ActorContext | `/auth/register`, `/login`, `/refresh`, `/logout`, `/me`; Register/Login/Profile UI | Auth PostgreSQL integration, CSRF/Origin/CORS, inactive/duplicate/missing-phone, browser route smoke | DONE |
| FR-SPE-01, FR-SPE-02, FR-SPE-03 | 3, 4, 5 | Specialty CRUD/status; Admin authorization | `/specialties`; public detail/list; Admin UI | Backend service/API + Frontend RTL | DONE |
| FR-DOC-01, FR-DOC-02, FR-DOC-03 | 3, 4, 5 | Doctor list/detail/filter and Admin master-data management | `/doctors`; public/Admin UI | Backend service/API + Frontend filtering/detail/admin tests | DONE |
| FR-SCH-01, FR-SCH-02, FR-SCH-03, FR-SCH-04, FR-SCH-05 | 3, 4, 6 | Schedule CRUD/status, generation, available slots, block/unblock; advisory lock overlap protection | `/schedules`; Doctor schedule and booking UI | validation, duplicate/overlap, adjacent ranges, concurrent overlap race | DONE |
| FR-APT-01, FR-APT-02, FR-APT-03, FR-APT-04, FR-APT-05, FR-APT-06, FR-APT-07, FR-APT-08 | 3, 4, 6, 13 | `SELECT FOR UPDATE`, occupied-slot partial unique index, transaction booking/cancel/rebook/state transitions | `/appointments`; Patient/Doctor Appointment UI | five concurrent bookings → one success; cancel boundary; transitions; rollback; E2E service integration | DONE |
| FR-DOCS-01, FR-DOCS-02, FR-DOCS-03, FR-DOCS-04, FR-DOCS-05, FR-DOCS-06 | 3, 4, 8, 13 | Document metadata/review, APPROVED-only ingestion, status/error, re-ingest replacement/dedup | `/documents`; Admin Document UI; controlled scripts | governance + JSON/CSV/PDF/DOCX + rollback/re-ingest tests | DONE |
| FR-CHAT-01, FR-CHAT-02, FR-CHAT-03, FR-CHAT-04, FR-CHAT-05, FR-CHAT-06 | 7, 10, 13 | Gemini text chat; short request/session context; safety/fallback; rule-first Risk Alert | `/chat/messages`; Chat UI | provider failure, fallback, safety, risk positive/negative/false-positive | DONE |
| FR-RAG-01, FR-RAG-02, FR-RAG-03, FR-RAG-04 | 8, 12, 13 | BGE-M3, pgvector Top-K, sources, no-context fallback, fixed evaluation | Chat answer + source traceability; evaluation scripts | 50-query grounded benchmark; strategy/plan/source/privacy regression | DONE |
| FR-RAG-05, FR-RAG-06 | 12 | Hybrid BM25+RRF and BGE reranker experiments on same corpus/query set | Configurable backend strategies; no separate UI | measured V2/V3 comparison | DONE experiment; not runtime default |
| FR-TOOL-01, FR-TOOL-02, FR-TOOL-03, FR-TOOL-04, FR-TOOL-05, FR-TOOL-06, FR-TOOL-07 | 9, 10, 13 | Registry/structured args; identity from ActorContext; existing business services; explicit booking confirmation | Chat tool results + `/chat/bookings/confirm` | spoofing, invalid args, timeout/failure, confirmation/conflict/repeat | DONE |
| FR-HO-01, FR-HO-02, FR-HO-03 | 3, 10, 11, 13 | Persistent HandoffService workflow + WebSocket notification/status | `/handoffs`; `/handoffs/ws`; Handoff UI | REST/RBAC/state/reconnect/failure/authoritative reload | DONE |
| FR-HO-04 | 11 | SRS defines live Patient-Staff chat outside MVP; current system provides ticket + notification/status | No live-chat endpoint/UI | Scope audit | FUTURE WORK by design |
| FR-VOICE-01, FR-VOICE-02, FR-VOICE-03, FR-VOICE-04, FR-VOICE-05 | 11, 13 | Browser push-to-talk, faster-whisper, editable transcript, existing chat pipeline, SpeechSynthesis fallback | `/voice/transcriptions`; Voice controls in Chat UI | audio/format/cleanup/failure + Frontend browser API/TTS tests; historical live mic verification | DONE WITH LIMITATION: Vietnamese STT quality |
| FR-VOICE-06 | 11 | SSE is optional Could; current response remains request/response | No SSE required for acceptance | Scope audit | FUTURE WORK by design |
| FR-MR-01, FR-MR-02, FR-MR-03, FR-MR-04, FR-MR-05, FR-MR-06 | 2–6, 13 | Appointment 1:0..1 record; COMPLETED/ownership rules; Patient own-read; no delete; metadata-only audit; AI isolation | `/medical-records`; Doctor form + Patient read-only history/detail | terminal states, duplicate, ownership, role/privacy, audit and AI source/tool isolation | DONE |
| BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, BR-07 | 2–6 | slot/appointment constraints and transactions; Backend authoritative; business data from PostgreSQL | Booking/cancel APIs and UI | constraint/concurrency/rollback/authorization tests | DONE |
| BR-08, BR-09, BR-10, BR-11, BR-12, BR-13 | 7–11 | trusted ActorContext; explicit confirm; medical safety; sources/fallback; governed corpus; Voice reuses chat | Chat/RAG/Tool/Voice/Handoff UI/APIs | AI/tool/risk/voice integration regression | DONE |
| BR-14, BR-15, BR-16, BR-17, BR-18, BR-19, BR-20 | 2–11 | one primary Specialty/Doctor; minimal Patient profile; Staff scope; Admin approval; ticket WebSocket; Vietnamese push-to-talk; no external appointment notification | Existing role-specific UI/APIs | schema, RBAC, workflow and scope tests/audit | DONE for MVP |
| BR-21, BR-22, BR-23, BR-24 | 2–6, 13 | MedicalRecord cardinality, ownership/privacy, no hard delete, audit, AI isolation | MedicalRecord service/API/UI | database + service + API + Frontend tests | DONE |
| NFR-SEC-01, NFR-SEC-02, NFR-SEC-03, NFR-SEC-04 | 5, 7, 13 | Argon2; Backend-only secrets; token/cookie security; CSRF/Origin/CORS; sanitized logs/errors; rate limit/headers | Auth and protected API boundary | security hardening tests; `pip-audit`/`npm audit`; source secret scan | DONE |
| NFR-PRIV-01, NFR-PRIV-02 | 2–13 | public/synthetic data only; clinical content isolated from AI, Staff/Admin default access and audit metadata | Role-protected MedicalRecord; governed Document corpus | privacy/ownership/source/tool-name tests | DONE |
| NFR-DATA-01, NFR-DATA-02, NFR-DATA-03 | 2, 6, 8, 13 | booking constraint/lock; Document FK/re-ingest; MedicalRecord FK+UNIQUE and service rules | Business/Document/MedicalRecord APIs | DB integration, concurrency, ingestion, duplicate/terminal-state tests | DONE |
| NFR-REL-01, NFR-REL-02 | 7–13 | provider/AI/Voice/WebSocket failure isolation; stable sanitized errors | fallback UI and direct Business MVP | failure-path regression and manual/demo fallback plan | DONE |
| NFR-PERF-01 | 12, 13, 14 | only measured evidence is reported; unbenchmarked operations marked NOT MEASURED | Performance report | fixed methodology/sample recorded | DONE |
| NFR-MNT-01, NFR-MNT-02 | 1–14 | Modular Monolith; feature-based frontend; Alembic-only schema evolution | project structure and scripts | compile/lint/build; Alembic current/heads/check | DONE |
| NFR-USAB-01, NFR-USAB-02 | 4, 10, 11, 13 | loading/error/empty/success; role UI; Voice state/fallback; lazy routes | all main Frontend pages | 37 RTL/Vitest + scoped Playwright smoke | DONE |
| NFR-AI-01, NFR-AI-02, NFR-AI-03, NFR-AI-04 | 7–13 | medical safety prompt/fallback; benchmark-based strategy; deterministic risk rules | Chat/RAG/Risk/Handoff UI | AI/RAG/risk/failure regression; 50-query benchmark | DONE |
| NFR-TEST-01, NFR-TEST-02 | 1–14 | automated business/concurrency/privacy suite and final matrix | Backend, Frontend, E2E suites | 160 Backend; 37 Frontend; 3 scoped Playwright at Phase 13 checkpoint | DONE |
| NFR-COMP-01 | 1–14 | native Windows 11/PowerShell setup; modern browser; no Docker/WSL/Linux requirement | README run/setup instructions | actual Windows development/test environment | DONE WITH HARDWARE LIMITATION for Voice quality |
| NFR-RT-01 | 11, 13 | PostgreSQL/REST source of truth; WebSocket notification/status only | Handoff REST + WS + UI reload | disconnect/reconnect/failure tests | DONE |
| UC-01, UC-02, UC-03, UC-04 | 3–6 | login; discovery; manual booking; cancellation | Auth/Discovery/Booking/Appointment UI | service/API/UI tests and Business MVP integration | DONE |
| UC-05, UC-06, UC-07 | 8–10 | RAG query; business tools; explicit-confirm AI booking | Chat UI and confirm endpoint | RAG/tool/booking confirmation tests | DONE |
| UC-08, UC-09, UC-10, UC-11 | 10–11 | handoff; STT; TTS; rule-based Risk Alert escalation | Handoff/Voice/Chat UI | backend/frontend regression; live Voice quality limitation documented | DONE WITH VOICE LIMITATION |
| UC-12, UC-13 | 3–6, 13 | Doctor create/update result; Patient read-only history | MedicalRecord UI/API | ownership/state/privacy/E2E tests | DONE |
| AC-BIZ-01, AC-BIZ-02, AC-BIZ-03, AC-BIZ-04, AC-BIZ-05, AC-BIZ-06, AC-BIZ-07 | 5, 6, 13 | Auth/RBAC, discovery, booking/concurrency/cancel, failure isolation, MedicalRecord workflow | Business MVP Frontend + Backend | PostgreSQL integration + RTL + scoped browser smoke | PASS |
| AC-AI-01, AC-AI-02, AC-AI-03, AC-AI-04, AC-AI-05, AC-AI-06, AC-AI-07, AC-AI-08 | 7–13 | Gemini, governed ingestion/RAG/sources, tools/confirmation, handoff, risk, WebSocket | Chat/Document/Handoff UI/APIs | AI/RAG/tool/risk/handoff regression | PASS |
| AC-VOICE-01, AC-VOICE-02, AC-VOICE-03 | 11, 13 | audio upload/STT or clear failure; same chat pipeline; browser TTS/text fallback | Voice controls | automated regression + historical physical microphone run | PASS functionality; quality limitation accepted |
| AC-MR-01, AC-MR-02, AC-MR-03, AC-MR-04 | 3–6, 13 | completed-only unique record; own-read; privacy/audit/no-delete/AI isolation; business-independent access | MedicalRecord UI/API | full privacy/state/failure regression | PASS |
| DR-01, DR-02, DR-03, DR-04, DR-05 | 2–8 | Specialty cardinality; Staff scope; cancel rule; minimal Patient profile; Admin RAG approval | Schema/services/UI | design + RBAC/business/document tests | IMPLEMENTED |
| DR-06, DR-07, DR-08, DR-09, DR-10 | 3–13 | Handoff ticket+WS; rule-based risk; Vietnamese push-to-talk; no email/SMS/push; basic MedicalRecord | Existing modules only | scope + workflow + privacy tests | IMPLEMENTED for MVP |

## Final coverage notes

- All SRS v1.1 FR, BR, NFR, UC, AC and DR identifiers are represented above.
- Full multi-role/Gemini/WebSocket/microphone browser automation is not claimed. Playwright remains a scoped release smoke; other layers use PostgreSQL integration, unit/component tests and recorded manual evidence.
- MedicalRecord is never a RAG source, Gemini context, Tool Calling target or Voice AI context.
- Full `vietnamese-medical-dataset.json` was not downloaded/ingested. RAG evaluation uses a large controlled subset.
