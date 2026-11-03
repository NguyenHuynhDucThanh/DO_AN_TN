# Phase 13 Testing Security and Evaluation

Ngày nghiệm thu: 30/10/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

SRS v1.1 là source of truth. Phase 13 harden và đánh giá implementation hiện có; không thay đổi SRS, business architecture, roadmap hoặc bắt đầu Phase 14.

## 1. Pre audit

### Already correct and reused

- Modular Monolith, PostgreSQL transaction và business services Phase 3/6.
- JWT/refresh rotation, Argon2, HttpOnly cookie, CSRF, exact Origin/CORS và ActorContext Phase 5.
- Document governance, streaming JSON, batched embedding, pgvector/RAG strategies Phase 8/12.
- Gemini/Tool/Risk/Handoff/Voice failure isolation Phase 7–11.
- MedicalRecord ownership, privacy, audit metadata-only và AI hard isolation.

### Needs hardening

- Chưa có application-level rate limit cho auth và endpoint tốn tài nguyên.
- Unexpected 500 chưa có JSON contract riêng; security headers chưa được áp dụng tập trung.
- Frontend route import eager tạo một chunk 878,33 kB.
- Playwright chưa có executable release smoke trong project.

### Bugs/security issues found

- `check_database.py` hard-code Alembic head cũ `0003` dù head hợp lệ là `0004`.
- CSV loader có thể giữ cột `negative` trong metadata dù JSON loader đã loại.
- Dependency audit phát hiện advisory ở PyJWT 2.10.1, python-multipart 0.0.20 và transitive fast-uri 3.1.8.

## 2. Reused hardened fixed optimized and new tests

**REUSED:** toàn bộ business/Auth/RAG/AI/Voice/Handoff implementation và test Phase 1–12.

**HARDENED:** rate limiter in-process có key BLAKE2 hash, tối đa 10.000 bucket; 429 + Retry-After; production không thể tắt; unexpected error được sanitize; security headers; production CORS không cho `X-Dev-User-Id`.

**FIXED:** CSV `negative` exclusion; Alembic head discovery động; dependency vulnerabilities.

**OPTIMIZED:** route-level `React.lazy`/dynamic import với loading fallback.

**NEW TESTS:** Phase 13 rate-limit/error/header/CSV/AI-tool-boundary/production-config tests; MedicalRecord terminal states; Playwright release smoke.

## 3. Regression results

| Gate | Result |
| --- | --- |
| Backend full suite + PostgreSQL integration | 160/160 PASS |
| Frontend Vitest/RTL | 37/37 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS |
| Playwright Edge release smoke | 3/3 PASS |
| Python compileall / `pip check` | PASS |
| `pip-audit` | No known vulnerabilities |
| `npm audit --audit-level=moderate` | 0 vulnerabilities |
| Synthetic seed, chạy hai lần | PASS idempotent |

Failure isolation regression xác nhận Gemini/RAG/embedding/tool/Voice/WebSocket không trở thành dependency của Auth, Specialty, Doctor, Schedule, Appointment hoặc MedicalRecord. Text chat vẫn dùng được khi Voice lỗi; Handoff REST/PostgreSQL vẫn authoritative khi WebSocket lỗi.

## 4. Security findings

| Severity | Finding | Resolution / acceptance | Status |
| --- | --- | --- | --- |
| HIGH | Dependency advisory trên auth JWT và multipart parser | PyJWT 2.15.0; python-multipart 0.0.31; audit lại sạch | FIXED |
| MEDIUM | Không có application brute-force/resource rate limit | Thêm limiter cho register/login/refresh/chat/ingestion/voice; production bắt buộc bật | FIXED |
| MEDIUM | CSV `negative` có thể vào metadata corpus | Loại `negative`; thêm regression test | FIXED |
| MEDIUM | fast-uri 3.1.8 advisory gián tiếp | Lockfile nâng 3.1.9; npm audit sạch | FIXED |
| LOW | Unexpected exception phụ thuộc default 500 response | Stable sanitized JSON 500, không echo exception/provider detail | FIXED |
| LOW | Thiếu response security headers | nosniff, frame deny, no-referrer, permissions policy; HSTS production | FIXED |
| LOW | DB checker báo sai vì hard-code migration cũ | Lấy current head từ Alembic ScriptDirectory | FIXED |
| LOW | Limiter chỉ chia sẻ trong một process | Phù hợp single-instance demo; multi-instance cần shared ingress/reverse-proxy limit | ACCEPTED deployment limitation |

Không còn CRITICAL/HIGH chưa xử lý. `.env`, raw/processed corpus và `dist` được Git ignore. Secret scan theo pattern chỉ in tên file và không phát hiện credential trong source được theo dõi; Gemini key/DB/JWT không được đưa vào frontend hoặc response/log.

## 5. Database validation

- Chain: `0001_enable_pgvector → 0002_create_business_schema → 0003_phase2_invariants → 0004_add_json_document_type`.
- `alembic current` và `heads`: `0004_add_json_document_type (head)`.
- `alembic check`: no new upgrade operations.
- PostgreSQL 18.6; pgvector 0.8.7; VECTOR(1024) và cosine smoke PASS.
- FK, UNIQUE, CHECK, partial occupied-slot index, HNSW, ON DELETE, rollback và model/schema parity PASS.
- Không sửa migration lịch sử và không tạo migration Phase 13.

## 6. Appointment concurrency and MedicalRecord privacy

Concurrency dùng PostgreSQL thật: năm transaction đặt cùng slot chỉ có một thành công; request còn lại conflict và slot/appointment giữ nhất quán. Schedule overlap race được serialize bằng advisory transaction lock; adjacent range hợp lệ.

MedicalRecord test thêm CONFIRMED, CANCELLED và NO_SHOW đều bị từ chối; chỉ COMPLETED và đúng Doctor được tạo. Duplicate trả conflict; Doctor khác/Patient update/Staff/Admin clinical-read bị chặn; Patient chỉ đọc record của mình; không có DELETE. Audit chỉ chứa metadata và không chứa symptoms/notes/conclusion/instructions.

Source audit xác nhận không có tool `get_medical_record`, `search_patient_history`, `summarize_medical_record` hoặc `update_medical_record`; MedicalRecord không vào loader, DocumentChunk, embedding, Dense/BM25/reranker, Gemini context, Voice context hoặc AI log.

## 7. Document and large dataset evaluation

- JSON dùng `ijson` streaming cho array/object-array và iterator từng dòng cho JSONL; không `json.load()` toàn file lớn.
- Embedding pending list bị chặn bởi batch size; progress mỗi 1.000 record; checksum/path/size/type được kiểm tra.
- APPROVED-only; PENDING/REJECTED bị chặn; re-ingest replace trong transaction; failure ghi FAILED và cleanup/rollback.
- JSON positive là factual content; negative bị loại; anchor chỉ làm evaluation metadata/query; article/category/title/content hash được giữ.
- CSV UTF-8/malformed/content mapping; PDF text/page/no-text; DOCX paragraph/heading/Unicode đều có regression. OCR vẫn ngoài scope.

Full `vietnamese-medical-dataset.json` khoảng 1 GB **không tồn tại và chưa được ingest**. Phase 13 tiếp tục dùng bằng chứng **LARGE CONTROLLED SUBSET**: file 900.991 bytes, 400 raw, 199 unique/embedded chunks mới, 209 DB chunks khi benchmark. Không gọi đây là full dataset.

## 8. RAG AI Tool Risk Handoff and Voice

Phase 12 benchmark không chạy lại vì regression không phát hiện bug strategy. Fixed 50-query results và final `hnsw_dense` giữ nguyên; exact dense là baseline/fallback, V2/V3 là experiment.

Live natural-query check trên corpus hiện tại:

- “nay mệt với sổ mũi”: kết quả liên quan viêm họng/viêm xoang.
- “đau họng với hơi sốt thì sao”: kết quả viêm họng liên quan rõ.
- “hay chóng mặt khi đứng lên”: kết quả còn mixed/overbroad, gồm rối loạn thần kinh và đột quỵ.

Đây là retrieval observation, không phải chẩn đoán. Safety prompt vẫn cấm chẩn đoán/kê đơn và yêu cầu nói rõ giới hạn. Query thứ ba được giữ thành known corpus/evaluation limitation.

Tool selection/structured args/fake identity/role spoof/timeout/service error/booking confirmation/conflict/repeat đều PASS. Tool Layer gọi business services, không ORM/SQL trực tiếp. Risk Alert rule-based chạy trước Gemini và Handoff reuse workflow hiện có.

Voice implementation regression PASS: upload/format/size/empty/STT failure/temp cleanup và Browser API/TTS fallback. Live microphone pipeline lịch sử PASS nhưng chất lượng nhận dạng tiếng Việt vẫn **LIMITED / FUTURE IMPROVEMENT**; không tải model lớn, tuning CUDA hoặc rewrite Voice trong Phase 13.

## 9. Frontend bundle analysis

| Item | Before | After |
| --- | ---: | ---: |
| Largest JS chunk | 878,33 kB | 398,03 kB |
| Gzip largest chunk | 269,74 kB | 124,41 kB |
| Chunk >500 kB warning | Có | Không |
| Build | PASS | PASS |

Thay đổi chỉ lazy-load feature pages; Home/AppShell và routing boundary giữ nguyên. Mức giảm largest chunk khoảng 54,7%. Vitest, lint, build và Playwright đều PASS sau tối ưu.

## 10. Performance evidence

Môi trường: cùng máy Windows development, PostgreSQL local.

| Measurement | Method/sample | Result |
| --- | --- | --- |
| Health REST | 50 sequential TestClient requests, real DB/vector check | mean 7,826 ms; median 2,875 ms; p95 3,628 ms |
| Exact retrieval | Phase 12, 50 query, Top-K=5 | mean 5,429 ms; median 3,370 ms; p95 6,158 ms |
| HNSW retrieval | Phase 12, 50 query, ef_search=40 | mean 3,987 ms; median 3,692 ms; p95 6,234 ms |
| Hybrid RRF | Phase 12, 50 query | mean 69,005 ms |
| Hybrid reranker CPU | Phase 12, 50 query | median 8.221,624 ms; not production default |
| Ingestion | 400 raw/199 chunk large subset | 140,286 giây |
| Frontend bundle | Vite production build | 878,33 → 398,03 kB largest chunk |

Auth, booking, Gemini, Tool và STT latency không được báo vì chưa có benchmark method/sample cố định trong Phase 13. Concurrency invariant được ưu tiên hơn tạo số latency không đáng tin.

## 11. Playwright scope

Edge release smoke 3/3 PASS trên Backend/Frontend/PostgreSQL thật, cổng riêng 8013/5174:

- health và public Specialty/Doctor discovery;
- protected route redirect;
- access/refresh token không nằm localStorage;
- registration validation không gửi malformed form.

Full multi-role mutation/Gemini/WebSocket/microphone Playwright chưa được tự động hóa vì cần demo credentials, provider quota và hardware permission. Các flow này có PostgreSQL API integration, Vitest/mock và manual historical evidence; không được báo là full Playwright PASS.

## 12. Known issues and deferred items

- Vietnamese STT accuracy trên CPU demo còn thấp; functionality hoạt động nhưng quality tuning là future improvement.
- Full ~1 GB dataset chưa ingest; chỉ large controlled subset.
- Natural “chóng mặt” retrieval còn mixed do corpus/evaluation coverage.
- Rate limiter là per-process; multi-instance cần shared platform/reverse-proxy policy.
- Full multi-role/provider/hardware Playwright flow chưa automated.
- DOCX loader dùng python-docx in-memory, phù hợp document thông thường; large dataset chính là JSON streaming.
- Large ingestion qua HTTP là synchronous; dùng script/controlled admin operation cho corpus lớn.

## 13. Release readiness

- Required regression PASS.
- Business MVP/Auth/concurrency/MedicalRecord privacy PASS.
- JSON/CSV/PDF/DOCX và large-data claim đúng sự thật.
- RAG/Tool/Risk/Handoff/Voice functionality PASS với limitation rõ.
- Frontend test/lint/build/E2E PASS.
- Dependency audit sạch; không còn CRITICAL/HIGH chưa xử lý.
- Không schema change/migration Phase 13.

**RELEASE READINESS: PASS cho phạm vi đồ án/demo có kiểm soát.** Production Internet deployment vẫn phải cấu hình HTTPS/domain/secret, backup/monitoring và shared edge rate limit theo nền tảng host.

## 14. Kết luận

**PHASE 13: PASS.**

Phase 14 chưa được bắt đầu.
