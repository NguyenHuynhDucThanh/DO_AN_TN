# Phase 3 Core Backend CRUD and Medical Record

Ngày hoàn thành: 20/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

## Kết quả

Backend dùng Modular Monolith theo luồng Router → Service → Repository/Data Access → SQLAlchemy → PostgreSQL. Models và migrations Phase 2 được giữ nguyên; `alembic check` xác nhận Phase 3 không cần migration mới.

| Module | Chức năng Phase 3 |
| --- | --- |
| auth/users | ActorContext; development/test chỉ nhận user ID và lấy role thật từ database; production trả 401. |
| specialties | List, detail, create, update, bật/tắt; Admin quản lý. |
| doctors | List, detail, filter specialty, create/update master data; Admin quản lý. |
| schedules | Schedule create/update/cancel-status, chống overlap bằng advisory lock, slot generation, available slots, block/unblock. |
| appointments | Booking khóa slot FOR UPDATE, cancel/rebook đúng BR-04, list/detail theo actor, Doctor cập nhật COMPLETED/NO_SHOW. |
| medical_records | Create/get/update/history; completed-only, assigned-doctor-only, Patient own-read, không DELETE, metadata-only audit. |
| documents | Metadata create/list/detail/update/delete có điều kiện và Admin APPROVE/REJECT; chưa ingest/embedding. |
| handoffs | Ticket create/list/detail, assign Staff/Admin, PENDING → IN_PROGRESS → RESOLVED; chưa WebSocket. |

## Bảo mật tạm thời

Phase 5 mới triển khai JWT/refresh token/RBAC đầy đủ. Phase 3 không dùng header role. `X-Dev-User-Id` chỉ hoạt động ở development/test; backend xác minh User active và đọc role active từ PostgreSQL. Production luôn 401. Service nhận `ActorContext`, nên Phase 5 có thể thay dependency xác thực mà không viết lại business logic.

MedicalRecord không có API DELETE. Staff/Admin không được mặc nhiên đọc nội dung lâm sàng. Audit create/update chỉ chứa appointment ID hoặc tên field thay đổi, không chứa nội dung khám.

## Transaction và consistency

- Schedule lấy advisory transaction lock theo Doctor trước khi kiểm tra overlap.
- Slot generation chỉ chạy một lần; range phải chia hết duration.
- Booking khóa ScheduleSlot bằng `FOR UPDATE`, kiểm tra AVAILABLE và unique index trước khi đổi BOOKED.
- Appointment cancellation và giải phóng slot nằm trong cùng transaction.
- MedicalRecord khóa Appointment/record, kiểm tra COMPLETED và Doctor ownership; UNIQUE appointment_id chống race, IntegrityError rollback thành 409.
- Integration test dùng outer transaction/savepoint và rollback toàn bộ dữ liệu test.

## Error contract

- 400: dữ liệu nghiệp vụ/time range/outcome không hợp lệ.
- 401: thiếu actor hoặc dependency dev bị tắt.
- 403: sai role/ownership, gồm Staff/Admin đọc MedicalRecord.
- 404: entity không tồn tại.
- 409: trạng thái, overlap, duplicate hoặc slot conflict.
- 422: FastAPI/Pydantic validation.
- 500: lỗi ngoài dự kiến, không expose DSN/secret.

## Kiểm thử

- Specialty/Doctor CRUD và rollback sau unique conflict.
- Schedule invalid time, overlap, slot generation, duplicate và blocked slot.
- Appointment booking, blocked slot, cancel và rebook.
- MedicalRecord create, duplicate 409, invalid Appointment, update, unauthorized actor, patient history và audit privacy.
- Document metadata/review; Handoff state workflow.
- API error contract, 401 thiếu actor, role lấy từ DB và 403 clinical data.
- Toàn bộ Phase 1/2 regression tests chạy cùng Phase 3.

MedicalRecord không có DELETE. Document metadata có DELETE riêng chỉ cho Admin khi bản ghi còn PENDING, chưa ingest và chưa có chunk; thao tác được audit.

Kết quả cuối: **38/38 tests pass** với PostgreSQL integration; `alembic check` không phát hiện schema drift; OpenAPI có 24 paths và 37 operations. DELETE duy nhất là Document metadata có điều kiện nêu trên.

## Ngoài phạm vi

- Không Frontend Phase 4.
- Không JWT/Refresh Token/Argon2/CSRF hoàn chỉnh Phase 5.
- Không Gemini, RAG, embedding, Tool Calling hoặc ingestion.
- Không WebSocket, Voice hoặc background worker.

## Checklist

- [x] Modular Monolith đúng lớp
- [x] Specialty CRUD
- [x] Doctor CRUD và filter
- [x] Schedule validation, overlap và slot generation
- [x] Appointment transaction và blocked-slot rules
- [x] MedicalRecord service, privacy, audit và không hard-delete
- [x] Actor context sẵn sàng tích hợp Phase 5
- [x] Document metadata không ingestion
- [x] Handoff ticket workflow
- [x] Error contract
- [x] Tests pass
- [x] Không triển khai Phase 4
