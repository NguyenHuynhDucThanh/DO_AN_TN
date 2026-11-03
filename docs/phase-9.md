# Phase 9 — Tool Calling

Ngày nghiệm thu: 26/10/2026. SRS v1.1 là source of truth; SRS, roadmap và schema database không bị thay đổi. Phase 9 mở rộng Gemini/Chat/RAG và tái sử dụng toàn bộ business services hiện có.

## Phân loại trước implementation

| Nhóm | Kết quả audit |
| --- | --- |
| ALREADY IMPLEMENTED / REUSED | `ActorContext` + JWT/RBAC; `SpecialtyService`, `DoctorService`, `ScheduleService`, `AppointmentService`, `HandoffService`; GeminiClient/ChatService; RAG V1; Chat UI. |
| PARTIALLY IMPLEMENTED / EXTENDED | Specialty chưa có search text; Schedule chưa có service read một slot đầy đủ quan hệ; Gemini chưa nhận tool declaration; response/UI chưa có tool result và confirmation. |
| NOT IMPLEMENTED / NEW | Tool registry/validation/executor; Gemini manual function-call turn; orchestrator; signed actor-bound booking confirmation; confirmation endpoint/card; Phase 9 tests. |

## Kiến trúc thực tế

```text
User → React Chat UI → Chat Orchestrator → Gemini structured function call
     → ToolExecutor validation + ActorContext
     → existing Business Service → PostgreSQL
     → structured tool result → Gemini final response
```

`ToolExecutor` là adapter. Nó không import SQLAlchemy/model/repository, không chạy SQL và không chứa lại booking/handoff workflow. Dữ liệu kiến thức tĩnh tiếp tục qua RAG; Specialty/Doctor/Slot/Booking/Handoff động đi qua tools.

## Tools

- `search_specialty(query)` gọi `SpecialtyService.search` trên Specialty ACTIVE.
- `list_doctors(specialty_id, filters)` gọi `DoctorService.list`.
- `available_slots(doctor_id, date)` gọi `ScheduleService.available_slots`, với ngày theo UTC+07.
- `create_booking(slot_id)` chỉ kiểm tra slot và sinh `CONFIRMATION_REQUIRED`; không tạo Appointment.
- `handoff_to_staff(reason)` gọi lại `HandoffService.create` với source `CHATBOT`.

Schema tool dùng Pydantic `extra=forbid`; không có `user_id`, `patient_id`, `role` hoặc doctor identity do model cung cấp. Identity duy nhất đến từ `ActorContext`. Registry không có MedicalRecord tool.

## Explicit booking confirmation

```text
Gemini chọn slot
→ create_booking
→ signed confirmation token (actor + slot + expiry 5 phút)
→ React hiển thị bác sĩ/chuyên khoa/ngày/giờ/slot
→ người dùng bấm “Xác nhận đặt lịch”
→ POST /api/v1/chat/bookings/confirm
→ existing AppointmentService.create
```

Câu tự do như “ok/ừ/được” không gọi transaction. Token của actor khác hoặc token sai/hết hạn bị từ chối. Booking thật vẫn dùng `SELECT FOR UPDATE`, trạng thái slot, partial unique index và trả 409 từ `AppointmentService`; xác nhận lặp lại không tạo lịch thứ hai.

## Frontend

Chat UI hiển thị tool status, lựa chọn Specialty/Doctor/Slot có dữ liệu thật, empty result, thẻ xác nhận và kết quả BOOKED. Lỗi 409 hiển thị thông báo slot vừa bị đặt và yêu cầu tìm slot khác. Token chỉ nằm trong state của thẻ xác nhận, không lưu localStorage và không đưa vào chat history.

## Bảo mật và ranh giới

- Tool declaration không nhận identity; Backend vẫn authoritative cho role/object authorization.
- Không có MedicalRecord tool/import/context và không gửi dữ liệu lâm sàng cho Gemini.
- Tool timeout/provider failure là lỗi có kiểm soát, không bị báo thành công.
- Không tạo service Handoff/Appointment thứ hai.
- Không triển khai Risk Alert, Voice, WebSocket, BM25/RRF/reranker hoặc Phase 10.

## Database và migration

Không có schema change. Alembic vẫn:

```text
0001_enable_pgvector
→ 0002_create_business_schema
→ 0003_phase2_invariants
→ 0004_add_json_document_type (head)
```

## Test và kiểm chứng

- Backend full regression với PostgreSQL thật: **111/111 PASS**.
- Phase 9 bao phủ registry/schema, malformed/unknown args, fake identity/role spoofing, unauthorized booking, Specialty search, no-result, no booking before confirmation, actor-bound confirmation, successful booking qua PostgreSQL thật, repeated confirmation/409, Handoff reuse, timeout, no direct ORM/SQL và no MedicalRecord tools.
- Frontend Vitest/RTL: **27/27 PASS**, gồm explicit button-only booking và 409 UI.
- Frontend ESLint: PASS, 0 warning.
- Frontend production build: PASS; chỉ còn cảnh báo bundle >500 kB không chặn build.
- Alembic `current` và `heads`: `0004_add_json_document_type`.
- Gemini API read-only smoke: model chọn đúng `search_specialty`, ToolExecutor trả `SUCCESS`, có final answer; không có confirmation/mutation.

## Files chính

- Backend: `app/ai/orchestrator.py`, `app/ai/tools/*`, `app/ai/gemini_client.py`, `app/ai/router.py`, `app/ai/schemas.py`, `app/ai/chat_service.py`.
- Business extension nhỏ: `app/specialties/service.py`, `app/schedules/service.py`, `app/schedules/repository.py`.
- Frontend: `src/features/chat/api.ts`, `src/features/chat/ChatPage.tsx`.
- Tests: `tests/test_phase9_tool_calling.py`, Phase 6 real-database confirmation test, `src/test/phase9.test.tsx`.

## Deferred đúng roadmap

- Risk Alert thuộc Phase 10.
- Voice + Handoff WebSocket thuộc Phase 11; Handoff REST hiện tại tiếp tục được reuse.
- RAG V2/V3 thuộc Phase 12.
- Security/evaluation sâu hơn thuộc Phase 13.

**PHASE 9: PASS.**

