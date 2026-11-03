# Post-Phase 14 Issue Register

Ngày cập nhật: 03/11/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

Tài liệu này ghi nhận các vấn đề phát hiện khi kiểm thử thủ công sau Phase 14. Các mục dưới đây chưa được coi là DONE cho tới khi implementation và regression bắt buộc PASS.

## Tổng hợp

| ID | Vấn đề | Phân loại | Mức ảnh hưởng | Trạng thái |
| --- | --- | --- | --- | --- |
| POST14-UX-01 | Admin phải nhập trực tiếp User UUID khi tạo Doctor profile | Frontend/API integration gap | Medium | PLANNED — NOT IMPLEMENTED |
| POST14-UX-02 | Doctor không thể tạo/sửa lịch hoặc sinh slot trên Frontend; Patient không thấy lịch trống | Frontend/business workflow integration gap | High đối với demo Business MVP | RECORDED — NOT IMPLEMENTED |

## POST14-UX-01 — Doctor profile yêu cầu nhập User UUID

### Hiện trạng

- Doctor profile phải liên kết với một User có role `DOCTOR`.
- Backend kiểm tra đúng User, role và unique constraint.
- Frontend yêu cầu Admin nhập `User UUID` thủ công.
- Không có API/UI liệt kê User ACTIVE có role DOCTOR nhưng chưa có Doctor profile.
- Bác sĩ demo `doctor.an@example.invalid` đã có Doctor profile; dùng lại UUID sẽ gây conflict.

### Hướng xử lý đã chốt

- Thêm endpoint Admin-only liệt kê Doctor candidates.
- Candidate phải ACTIVE, có role DOCTOR và chưa có Doctor profile.
- Thay ô UUID bằng dropdown tên + email.
- Giữ `DoctorService.create()` làm nguồn kiểm tra cuối cùng.
- Không tạo module/service/model/migration mới.
- Việc Admin tạo hoàn toàn một tài khoản Doctor mới không thuộc fix này và cần Change Request riêng.

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

Frontend hiện chỉ có:

- list schedule;
- list available slots;
- màn hình read-only.

Frontend chưa có create/update/cancel/generate/block/unblock mutation hoặc form tương ứng. Vì vậy đây không phải lỗi của ScheduleService mà là workflow Backend–Frontend chưa được nối đầy đủ.

### Hướng xử lý đề xuất

1. Mở rộng `features/schedules/api.ts` với create/update/generate/status mutations.
2. Thêm create schedule dialog cho Doctor:
   - ngày/giờ bắt đầu;
   - ngày/giờ kết thúc;
   - thời lượng slot;
   - timezone rõ ràng.
3. Sau khi tạo schedule, cho phép sinh slot. Nếu sinh slot lỗi, schedule vẫn hiển thị và có nút thử lại.
4. Cho phép sửa interval khi chưa có slot; Backend tiếp tục từ chối sửa interval khi đã sinh slot.
5. Cho phép hủy schedule theo state/rule hiện có.
6. Bổ sung API đọc toàn bộ slot của một schedule nếu cần quản lý cả AVAILABLE/BOOKED/BLOCKED sau reload.
7. Thêm UI block/unblock; slot BOOKED không được thay đổi.
8. Invalidate đúng schedule và available-slot queries sau mutation.
9. Có thể cải thiện seed để tạo một số slot AVAILABLE phục vụ demo, nhưng không dùng seed để thay thế chức năng quản lý lịch.

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

## Quy tắc xử lý hai issue

- Không gộp hai vấn đề thành một refactor Auth/Schedule lớn.
- Thực hiện từng issue và regression độc lập.
- Chỉ đánh DONE khi code, API/UI và test thật đã PASS.
- Nếu phát sinh yêu cầu Admin tạo tài khoản Doctor mới hoặc thay đổi nghiệp vụ lịch, phải đánh giá Change Request trước.
- Sau khi fix, cập nhật Phase 14, requirement traceability, final test matrix và demo script bằng kết quả thật.

