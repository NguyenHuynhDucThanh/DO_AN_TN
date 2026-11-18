# Post-Phase 14 Issue Register

Ngày cập nhật: 06/11/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

Tài liệu này ghi nhận các vấn đề phát hiện khi kiểm thử thủ công sau Phase 14 và kết quả xử lý đã được kiểm chứng.

## Tổng hợp

| ID | Vấn đề | Phân loại | Mức ảnh hưởng | Trạng thái |
| --- | --- | --- | --- | --- |
| POST14-UX-01 | Admin phải nhập trực tiếp User UUID khi tạo Doctor profile | Frontend/API integration gap | Medium | DONE — 06/11/2026 |
| POST14-UX-02 | Doctor không thể tạo/sửa lịch hoặc sinh slot trên Frontend; Patient không thấy lịch trống | Frontend/business workflow integration gap | High đối với demo Business MVP | DONE — 06/11/2026 |
| POST14-ENH-01 | Admin tạo đồng thời tài khoản User DOCTOR và Doctor profile | Workflow extension được người dùng chốt | Medium | DONE — 06/11/2026 |

## POST14-UX-01 — Doctor profile yêu cầu nhập User UUID

### Hiện trạng

- Doctor profile phải liên kết với một User có role `DOCTOR`.
- Backend kiểm tra đúng User, role và unique constraint.
- Frontend yêu cầu Admin nhập `User UUID` thủ công.
- Không có API/UI liệt kê User ACTIVE có role DOCTOR nhưng chưa có Doctor profile.
- Bác sĩ demo `doctor.an@example.invalid` đã có Doctor profile; dùng lại UUID sẽ gây conflict.

### Kết quả xử lý

- Thêm endpoint Admin-only liệt kê Doctor candidates.
- Candidate phải ACTIVE, có role DOCTOR và chưa có Doctor profile.
- Thay ô UUID bằng dropdown tên + email.
- Giữ `DoctorService.create()` làm nguồn kiểm tra cuối cùng.
- Không tạo module/service/model/migration mới.
- Theo quyết định bổ sung của người dùng, cùng Dialog còn hỗ trợ tạo User `ACTIVE`, gán role `DOCTOR` và Doctor profile trong một transaction qua endpoint provisioning.
- Mật khẩu khởi tạo dùng Argon2; audit không chứa mật khẩu; duplicate/error rollback toàn bộ transaction.

Kế hoạch chi tiết: `doctor-user-selection-fix-plan.md`.

## POST14-UX-02 — Doctor không có giao diện quản lý lịch

### Bằng chứng hiện tại

Database của Doctor demo có:

| Schedule | Tổng slot | AVAILABLE | BOOKED |
| --- | ---: | ---: | ---: |
| 15/10/2026 08:00–10:00 | 1 | 0 | 1 |
| 15/01/2030 08:00–10:00 | 1 | 0 | 1 |

Vì không có slot `AVAILABLE`, Patient không thấy lịch trống.

Backend đã có:

- `POST /api/v1/schedules` — tạo schedule;
- `PATCH /api/v1/schedules/{schedule_id}` — cập nhật/hủy schedule;
- `POST /api/v1/schedules/{schedule_id}/slots/generate` — sinh slot;
- `PATCH /api/v1/schedules/slots/{slot_id}/status` — block/unblock slot;
- overlap validation và advisory transaction lock;
- Doctor ownership và Staff/Admin authorization.

Frontend trước khi sửa chỉ có:

- list schedule;
- list available slots;
- màn hình read-only.

Khoảng trống này đã được xử lý bằng cách mở rộng đúng feature Schedule hiện có; không viết lại ScheduleService.

### Kết quả xử lý

1. Đã mở rộng `features/schedules/api.ts` với create/update/generate/status mutations.
2. Đã thêm create schedule dialog cho Doctor:
   - ngày/giờ bắt đầu;
   - ngày/giờ kết thúc;
   - thời lượng slot;
   - timezone rõ ràng.
3. Có thể sinh slot, retry khi lỗi, sửa interval khi chưa có slot và hủy theo Backend rule.
4. Đã bổ sung API bảo vệ đọc toàn bộ slot của một schedule.
5. UI cho block/unblock; slot BOOKED không có thao tác thay đổi.
6. Mutation invalidate đúng schedule/slot/available-slot queries.

### Test bắt buộc

Backend:

- Doctor tạo lịch của chính mình.
- Doctor khác bị 403.
- Staff/Admin theo quyền tạo/cập nhật được.
- lịch quá khứ, thời gian không hợp lệ và overlap bị từ chối.
- adjacent schedule hợp lệ.
- generate slot đúng số lượng và không duplicate.
- block/unblock đúng rule; BOOKED bị chặn.
- Patient thấy slot AVAILABLE sau khi tạo/sinh slot.

Frontend:

- create form validation;
- create schedule success/error/conflict;
- generate slots;
- update/cancel rule UX;
- block/unblock;
- loading/error/empty/success;
- query invalidation;
- Patient booking page hiển thị slot vừa tạo.

Regression cuối:

- Backend full suite với PostgreSQL integration.
- Frontend Vitest, ESLint và production build.
- Business MVP E2E hoặc Playwright flow Doctor tạo lịch → Patient thấy slot nếu bổ sung vào browser suite.

### Kiến trúc và schema

- Reuse `ScheduleService`, `ScheduleRepository`, router và model hiện có.
- Không tạo Schedule module/service/router thứ hai.
- Không sửa migration đã apply.
- Không cần migration nếu chỉ thêm endpoint đọc slot và Frontend mutations.

## Kết quả kiểm chứng

- Backend focused workflow tests: **12/12 PASS**.
- Backend full PostgreSQL regression: **162/162 PASS**.
- Frontend workflow tests mới: **4/4 PASS**.
- Frontend full regression: **41/41 PASS**; ESLint 0 warning; production build PASS.
- Không thay đổi schema và không tạo migration.

## Quy tắc xử lý hai issue

- Không gộp hai vấn đề thành một refactor Auth/Schedule lớn.
- Thực hiện từng issue và regression độc lập.
- Chỉ đánh DONE khi code, API/UI và test thật đã PASS.
- Yêu cầu Admin tạo tài khoản Doctor mới đã được người dùng quyết định bổ sung và triển khai bằng schema hiện có.
- Sau khi fix, cập nhật Phase 14, requirement traceability, final test matrix và demo script bằng kết quả thật.

