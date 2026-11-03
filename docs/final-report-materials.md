# Final Report Materials

## 1. Tổng quan hệ thống

**Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn** là một Modular Monolith gồm Frontend React/TypeScript và Backend FastAPI/Python, lưu dữ liệu nghiệp vụ và vector trong PostgreSQL + pgvector. Business MVP hoạt động độc lập; AI là lớp tích hợp thêm RAG, Tool Calling, Risk Alert, Handoff và Voice nhưng không thay Backend authorization/business rules.

Các sơ đồ System Architecture, Frontend/Backend, ERD, Use Case, Auth, Booking, MedicalRecord, Ingestion, RAG, Tool, Risk, Handoff và Voice nằm trong `final-architecture-diagrams.md`.

## 2. Business system và database

- `User` lưu identity/profile tối thiểu; `Role`/`UserRole` cung cấp PATIENT, DOCTOR, STAFF, ADMIN.
- Patient không có table riêng vì Patient là `User + PATIENT role` và MVP không lưu hồ sơ sức khỏe tự do. Doctor có table riêng do cần Specialty, license và professional profile.
- `Specialty 1:N Doctor`; `Doctor 1:N DoctorSchedule`; schedule sinh `ScheduleSlot`.
- Booking dùng transaction và `SELECT FOR UPDATE`; partial unique index chặn nhiều Appointment chiếm cùng slot ở `CONFIRMED`, `COMPLETED`, `NO_SHOW`.
- Tạo schedule dùng transaction advisory lock theo Doctor để kiểm tra overlap; khoảng tiếp giáp không bị coi là overlap.
- Appointment không hard-delete khi hủy; trạng thái và slot được cập nhật cùng transaction.
- `Appointment 1:0..1 MedicalRecord` được bảo đảm bằng FK + UNIQUE `appointment_id`.
- `Document 1:N DocumentChunk`; embedding `VECTOR(1024)` nằm trong PostgreSQL, không có ChromaDB độc lập.
- `Handoff` là ticket bền vững; `AuditLog` lưu hành động/metadata phù hợp.

## 3. MedicalRecord scope và privacy

MedicalRecord chỉ được tạo cho Appointment `COMPLETED` bởi Doctor phụ trách. Doctor đó được đọc/cập nhật; Patient chỉ đọc hồ sơ của mình; Staff/Admin không mặc nhiên đọc clinical content. Không có DELETE, đơn thuốc, xét nghiệm, file bệnh án hoặc tích hợp HIS/EMR. Audit chỉ ghi metadata, không ghi symptoms/notes/conclusion/instructions.

MedicalRecord không được đưa vào Document/DocumentChunk, embedding, RAG, Gemini, Tool Calling, Risk Alert input hoặc Voice AI context. Dữ liệu demo là synthetic.

## 4. Authentication và security

Mật khẩu dùng Argon2. Access JWT ngắn hạn mang identity tối thiểu; refresh token là opaque token chỉ lưu hash trong `RefreshSession`. Rotation, revocation, family/replaced-session relation và reuse handling hỗ trợ quản lý phiên. Cookie HttpOnly giữ token khỏi JavaScript; state-changing request dùng CSRF header và exact Origin/CORS. Backend tái tải User/roles và tạo ActorContext để kiểm tra role-level + object-level authorization.

`X-Dev-User-Id` chỉ là development/test tooling, không fallback khi JWT lỗi và bị production guard vô hiệu. API key Gemini ở Backend. Phase 13 thêm rate limit, security headers, sanitized 500 và dependency audit. Limiter in-process phù hợp single-instance demo; multi-instance cần shared edge policy.

## 5. Gemini chatbot (Phase 7)

Gemini text chatbot dùng SDK `google-genai`; `GEMINI_MODEL` configurable và API key Backend-only. Phase 7 chỉ có basic text generation, safety baseline và controlled provider failure; chưa có RAG/Tool ở phase đó. AI lỗi không làm mất Business MVP.

## 6. RAG V1 và dataset (Phase 8)

RAG V1 quản trị Document metadata/review; chỉ Admin APPROVE/REJECT và chỉ source APPROVED mới ingest. Loader hỗ trợ JSON/JSONL, UTF-8 CSV, PDF có text và DOCX; không OCR. Pipeline chuẩn hóa, deduplicate, chunk, BGE-M3, `VECTOR(1024)`, pgvector exact cosine Top-K. Answer giữ source traceability và có no-context fallback.

Exact retrieval được chọn làm V1 baseline vì dễ kiểm chứng và không phụ thuộc approximate index tuning. Dataset/benchmark chi tiết nằm trong `final-rag-dataset-performance.md`.

## 7. Tool Calling và AI booking (Phase 9)

```text
Gemini → Tool Layer → ActorContext/Auth → existing Business Service → PostgreSQL
```

LLM chỉ đề xuất tool/structured arguments. Backend validate input, identity, role và object ownership; model không truy cập ORM/SQL hoặc truyền identity đáng tin. Tool reuse Specialty/Doctor/Schedule/Appointment/Handoff services.

Booking qua chatbot luôn có explicit confirmation: model hiểu intent → tool tìm slot → Backend tạo summary + token ngắn hạn → UI hiển thị → user bấm Confirm → AppointmentService mới thực thi transaction. Risk/orchestrator không bypass quy tắc này.

## 8. AI MVP và Risk Alert (Phase 10)

Chat Orchestrator phân biệt risk/safety, knowledge query, business lookup, booking intent, handoff và fallback. Knowledge dùng RAG; dữ liệu động dùng Tools; provider/retrieval/tool failure không được bù bằng nội dung bịa.

Risk Alert là deterministic rule engine chạy trước Gemini. Khi trigger, hệ thống hiển thị cảnh báo an toàn không chẩn đoán và có thể tạo Handoff ưu tiên qua service hiện có. Đây là safety escalation, không phải diagnostic engine hoặc prescription system.

## 9. Voice, TTS và Handoff WebSocket (Phase 11)

Voice dùng microphone vật lý có sẵn qua browser `getUserMedia`/`MediaRecorder`, upload audio tới FastAPI, nhận dạng bằng faster-whisper, cleanup file tạm và đặt transcript có thể chỉnh sửa vào cùng chat text pipeline. Không có custom/virtual microphone hoặc Voice chatbot riêng.

TTS dùng `SpeechSynthesis`/`SpeechSynthesisUtterance` của browser; text luôn hiển thị và là fallback. Vietnamese STT quality thay đổi theo microphone/hardware/model và còn là known limitation.

Handoff REST/PostgreSQL giữ persistent state `PENDING → IN_PROGRESS → RESOLVED`; WebSocket chỉ notification/status. Khi WebSocket lỗi, UI reload state qua REST/DB. MVP không có live Patient-Staff chat.

## 10. RAG V2/V3 experiments (Phase 12)

Phase 12 so sánh Exact Dense, HNSW Dense, BM25+RRF và BGE reranker trên cùng corpus 209 chunks, 50 grounded query, Top-K=5. HNSW giữ cùng Hit@5/Recall@5/MRR với exact nhưng mean thấp hơn; V2 không cải thiện quality; V3 chỉ cải thiện nhỏ nhưng CPU latency nhiều giây. Runtime cuối là `hnsw_dense`, exact là baseline/fallback, V2/V3 giữ làm experiment/report.

## 11. Frontend

Frontend dùng React, TypeScript, Vite, Material UI, TanStack Query, Axios, React Hook Form, Zod và React Router. Backend vẫn authoritative cho authorization/business rules. TanStack Query quản lý server state/invalidation; forms dùng Zod cho UX validation. Phase 13 dùng `React.lazy`/dynamic import theo route, giảm largest JS chunk từ 878.33 kB xuống 398.03 kB và loại warning >500 kB.

## 12. Safety wording example

Với “nay mệt và sổ mũi”, hệ thống tạo BGE-M3 query embedding, lấy approved medical context rồi Gemini tạo câu trả lời có nguồn. Chatbot không nên kết luận “Bạn bị cúm”, mà nói “Những triệu chứng này có thể gặp trong…” và hướng dẫn tìm hỗ trợ y tế phù hợp nếu nặng/kéo dài. Retrieval assistance không tương đương chẩn đoán.

## 13. Scope statements for the thesis

- READY cho đồ án/demo có kiểm soát; không claim production-scale healthcare certification.
- Full 1 GB dataset chưa được ingest; báo cáo dùng large controlled subset.
- Playwright 3/3 là scoped release smoke, không phải full multi-role/provider/microphone browser automation.
- Auth/booking/Gemini/Tool/STT latency là NOT MEASURED vì chưa có methodology/sample cố định.
- MedicalRecord là hồ sơ kết quả khám cơ bản, không phải full HIS/EMR.
