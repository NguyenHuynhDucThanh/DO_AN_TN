# Phase 6 Business MVP

Ngày hoàn thành: 22/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

Phase 6 là giai đoạn audit, integration và E2E cho Business MVP. Không có service, router, model hay endpoint nghiệp vụ nào bị viết lại.

## 1. Requirements thực hiện

- Kiểm chứng nhiều transaction cùng đặt một `ScheduleSlot`: chỉ một booking thành công, các booking còn lại nhận 409.
- Kiểm chứng race condition khi hai request tạo lịch chồng lấn cho cùng Doctor và quy tắc cho phép hai khoảng liền kề.
- Kiểm chứng các transition `CONFIRMED → CANCELLED | COMPLETED | NO_SHOW`, transition sai và tính nhất quán của slot.
- Kiểm chứng ranh giới hủy: Patient chỉ hủy khi `now < slot.start_at`.
- Kiểm chứng Business MVP không cần Gemini, RAG, embedding hoặc voice.
- Kiểm chứng E2E MedicalRecord: completed-only, Doctor ownership, duplicate 409, Patient own-read/read-only, Staff/Admin không được đọc lâm sàng và audit không chứa clinical text.

## 2. ALREADY IMPLEMENTED được reuse

| Thành phần | Cách reuse |
| --- | --- |
| `ScheduleService` | Giữ nguyên validation, advisory transaction lock theo Doctor, overlap query, slot generation và block/unblock. |
| `AppointmentService` | Giữ nguyên `SELECT ... FOR UPDATE`, kiểm tra AVAILABLE, booking/cancel/rebook/outcome và transaction boundary. |
| `MedicalRecordService` | Giữ nguyên completed-only, Doctor ownership, Patient own-read, update và metadata-only audit. |
| Auth Phase 5 | Dùng JWT/refresh cookie, CSRF, exact Origin/CORS và `ActorContext` thật cho API E2E. |
| Frontend Phase 4/5 | Dùng nguyên các màn hình booking, appointment, Doctor workflow, MedicalRecord và auth. |
| Schema Phase 2 | Kiểm chứng lại `uq_appointments_occupied_slot` cho `CONFIRMED`, `COMPLETED`, `NO_SHOW`; không thay schema. |

## 3. PARTIALLY IMPLEMENTED được extend

- Concurrency của booking và schedule đã có cơ chế bảo vệ từ Phase 3; Phase 6 bổ sung test đa luồng với session/transaction PostgreSQL độc lập.
- Lifecycle appointment và cancellation đã được test theo luồng cơ bản; Phase 6 bổ sung terminal transition, object ownership, slot consistency và biên thời gian chính xác.
- MedicalRecord đã có backend, UI và auth; Phase 6 bổ sung một chuỗi E2E xác thực đầy đủ từ booking đến Patient history.

## 4. Thành phần NEW

- `tests/test_phase6_business_mvp_integration.py` gồm 5 integration tests chuyên biệt cho concurrency, race condition, state transition, cancellation boundary và authenticated Business/MedicalRecord E2E.
- Nhãn trạng thái trang chủ Frontend được đồng bộ thành `Business MVP · Phase 6`; không thay đổi luồng nghiệp vụ.

## 5. Files tạo/sửa

Tạo:

- `healthcare-backend/tests/test_phase6_business_mvp_integration.py`
- `docs/phase-6.md`

Sửa:

- `healthcare-frontend/src/pages/HomePage.tsx`
- `docs/requirement-traceability.md`
- `README.md`
- `healthcare-backend/README.md`
- `healthcare-frontend/README.md`

Không sửa business service, router, schema, model hoặc SRS.

## 6. Migration

Không có migration mới vì schema không thay đổi. Chuỗi hiện hành vẫn là:

```text
0001_enable_pgvector
→ 0002_create_business_schema
→ 0003_phase2_invariants
```

`alembic current` ở head `0003_phase2_invariants`; `alembic check` không phát hiện operation mới.

## 7. API/UI mới

Không có API, endpoint hoặc màn hình nghiệp vụ mới. Phase 6 sử dụng lại API Phase 3, UI Phase 4 và auth Phase 5. Chỉ có nhãn trang chủ được cập nhật để phản ánh phase hiện tại.

## 8. Tests

Năm test Phase 6 mới:

1. Concurrent booking: 5 worker cùng đặt một slot, kết quả 1 success + 4 conflict 409.
2. Schedule race: hai transaction tạo khoảng chồng lấn cho cùng Doctor, chỉ một commit; hai khoảng adjacent cùng hợp lệ.
3. Appointment transitions: kiểm tra COMPLETED/NO_SHOW/CANCELLED, transition sai, ownership và slot state.
4. Cancellation boundary: đúng `slot.start_at` thì bị từ chối, trước một microsecond thì được hủy.
5. Authenticated Business + MedicalRecord E2E qua FastAPI: register/login, tra cứu, book/cancel/book, complete, create/update/read record, privacy và audit.

## 9. Kết quả test thật

| Hạng mục | Kết quả |
| --- | --- |
| Riêng test Phase 6 với PostgreSQL thật | 5/5 PASS |
| Toàn bộ Backend Pytest với PostgreSQL integration | 51/51 PASS |
| Frontend Vitest + React Testing Library | 19/19 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; chỉ còn cảnh báo kích thước chunk không chặn build |
| Alembic | Head `0003_phase2_invariants`; check sạch |
| Live browser + Backend/PostgreSQL thật | PASS toàn bộ Patient → book → cancel → rebook → Doctor complete → create MedicalRecord → Patient read-only history; console không có error/warning |

Dữ liệu live chỉ là synthetic. Sau kiểm thử, schedule/slot/appointment/MedicalRecord/audit tạm được xóa, refresh session tạm bị thu hồi và password của tài khoản seed được khôi phục về sentinel.

## 10. Traceability

| Requirement | Implementation được kiểm chứng | Test |
| --- | --- | --- |
| FR-SCH-01..05, BR-05..07 | Advisory lock theo Doctor, overlap exclusion, adjacent range | Schedule race integration |
| FR-APT-01..08, BR-08..13 | Row lock, unique occupied slot, cancel/rebook, outcome và slot consistency | Concurrent booking, transition, boundary và authenticated E2E |
| FR-MR-01..06, BR-21..24 | Completed-only, 1:0..1, ownership, read-only, no hard-delete và privacy | Authenticated MedicalRecord E2E + live browser E2E |
| UC-01..07, UC-12/13 | Authenticated Patient/Doctor Business MVP | API E2E và live browser E2E |
| NFR-DATA-03, NFR-TEST-02 | DB constraint, transaction, rollback, privacy/audit | PostgreSQL integration suite 51/51 |

Chi tiết trạng thái Requirement → Phase → Implementation → Test → Status được đồng bộ trong `docs/requirement-traceability.md`.

## 11. Issues / deferred items

- Cảnh báo Vite về chunk lớn không làm build fail; có thể tối ưu code-splitting ở Phase 13 nếu cần.
- Rate limiting, brute-force protection và security evaluation tổng thể vẫn thuộc Phase 13.
- Gemini, RAG, embedding, Tool Calling, voice và WebSocket không được cấu hình trong Phase 6.
- Test concurrency cần PostgreSQL thật, schema ở Alembic head và `RUN_DB_INTEGRATION=1`.

## 12. Kết luận

**PHASE 6: PASS.** Business MVP hoạt động end-to-end trên Frontend, FastAPI và PostgreSQL thật mà không cần AI. Các service Phase 3, UI Phase 4 và auth Phase 5 được reuse; không có rewrite, schema change hay migration mới. Phase 7 chưa được bắt đầu.
