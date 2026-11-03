# Theo dõi lỗi và khoảng trống sau Phase 14

Ngày tạo: 03/11/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

File này theo dõi các vấn đề được phát hiện trong quá trình kiểm thử thủ công sau Phase 14. Không được đánh dấu `DONE` nếu code chưa triển khai hoặc test bắt buộc chưa PASS.

## Quy ước trạng thái

| Trạng thái | Ý nghĩa |
| --- | --- |
| `OPEN` | Đã xác nhận vấn đề, chưa triển khai sửa. |
| `PLANNED` | Đã có phương án xử lý được chốt. |
| `IN PROGRESS` | Đang sửa code. |
| `VERIFYING` | Đã sửa, đang chạy regression/manual verification. |
| `DONE` | Implementation và test bắt buộc đều PASS. |
| `DEFERRED` | Có lý do rõ ràng để chuyển sang Future Work/Change Request. |

## Tổng hợp

| ID | Vấn đề | Phân loại | Mức độ | Trạng thái |
| --- | --- | --- | --- | --- |
| ISSUE-001 | Admin phải nhập trực tiếp User UUID khi tạo Doctor profile | UX/Frontend–Backend integration gap | Medium | PLANNED — NOT IMPLEMENTED |
| ISSUE-002 | Doctor không thể tạo/sửa/sinh slot trên UI; Patient không thấy lịch trống | Business workflow/Frontend integration gap | High cho demo | OPEN — NOT IMPLEMENTED |

---

## ISSUE-001 — Doctor create form yêu cầu User UUID thủ công

### Hiện tượng

Admin đăng nhập, mở **Quản lý bác sĩ → Thêm hồ sơ bác sĩ** và phải tự nhập `User UUID`.

Admin không có màn hình/API để xem User role `DOCTOR` chưa có Doctor profile, nên không thể biết UUID hợp lệ bằng quy trình giao diện thông thường.

### Bằng chứng hiện tại

- Frontend `DoctorAdminPage` dùng `TextField` nhập `user_id` và validate UUID.
- `POST /doctors` yêu cầu `user_id`, `specialty_id`, `license_number`.
- Backend kiểm tra đúng rằng User phải tồn tại, có role `DOCTOR` và chưa có Doctor profile.
- User demo `doctor.an@example.invalid` đã có Doctor profile; nhập lại UUID sẽ nhận conflict.

### Nguyên nhân

Backend data invariant đúng nhưng thiếu read API dành cho Admin để lấy candidate. Frontend đưa khóa kỹ thuật UUID ra cho người dùng thay vì hiển thị tên/email.

### Phân loại phạm vi

Đây là UX/integration fix cho chức năng Doctor management hiện có, không viết lại Auth hoặc DoctorService và không cần migration.

Việc cho Admin tạo hoàn toàn một tài khoản Doctor mới là chức năng khác, liên quan account provisioning/password/role audit và cần Change Request riêng.

### Phương án đã chốt

Chi tiết đầy đủ nằm trong `doctor-user-selection-fix-plan.md`.

Tóm tắt:

1. Thêm `GET /api/v1/doctors/candidates`, chỉ Admin.
2. Chỉ trả User `ACTIVE`, có role `DOCTOR`, chưa có Doctor profile.
3. Response chỉ chứa `id`, `full_name`, `email`, `phone` cần thiết.
4. Thay ô UUID bằng dropdown `Họ tên — email`.
5. Giữ `DoctorService.create()` làm nguồn validation cuối.
6. Invalidate Doctor list và candidate query sau khi tạo.
7. Không tạo migration, service/router/model trùng.

### Test bắt buộc

- Admin xem candidates; Patient/Doctor/Staff bị 403.
- Loại User sai role, inactive hoặc đã có profile.
- Dropdown loading/error/empty/success.
- Không nhập UUID thủ công.
- Submit đúng `user_id`; duplicate/race trả 409 rõ ràng.
- Backend full regression; Frontend test/lint/build; Playwright smoke.

### Trạng thái

**PLANNED — NOT IMPLEMENTED.**

---

## ISSUE-002 — Doctor UI không quản lý được lịch và Patient không có slot trống

### Hiện tượng

- Patient tìm bác sĩ nhưng không thấy slot khả dụng.
- Doctor đăng nhập và chỉ xem được lịch; không thấy nút tạo, sửa, hủy, sinh slot hoặc block/unblock.

### Bằng chứng database ngày 03/11/2026

Bác sĩ demo có hai schedule:

| Schedule | Tổng slot | AVAILABLE | BOOKED | BLOCKED |
| --- | ---: | ---: | ---: | ---: |
| 15/10/2026 08:00–10:00 | 1 | 0 | 1 | 0 |
| 15/01/2030 08:00–10:00 | 1 | 0 | 1 | 0 |

Không có slot `AVAILABLE`, nên Patient không thể đặt lịch.

### Bằng chứng source

Backend đã có:

- `POST /api/v1/schedules` — tạo schedule.
- `PATCH /api/v1/schedules/{schedule_id}` — cập nhật/hủy.
- `POST /api/v1/schedules/{schedule_id}/slots/generate` — sinh slot.
- `PATCH /api/v1/schedules/slots/{slot_id}/status` — block/unblock.
- Kiểm tra future time, duration, overlap, advisory lock, Doctor ownership và booked-slot protection.

Frontend hiện chỉ có:

- `GET /schedules`.
- `GET /schedules/available-slots`.
- Màn hình read-only hiển thị schedule và slot AVAILABLE.

### Nguyên nhân

ScheduleService và API mutation đã được triển khai, nhưng Frontend Phase 4 chỉ nối luồng xem. Dữ liệu seed chỉ tạo một slot cho mỗi schedule và cả hai slot đều BOOKED, nên không có dữ liệu AVAILABLE che lấp khoảng trống UI này.

### Phân loại phạm vi

Đây là business workflow/Frontend integration gap có mức độ **High cho demo**, vì chặn luồng Patient tìm slot và Doctor tự chuẩn bị lịch.

Phải reuse `ScheduleService`, repository, router và database hiện có; không được viết lại concurrency/overlap logic.

### Phương án xử lý đề xuất

#### Frontend

1. Bổ sung API client:
   - `createSchedule`;
   - `updateSchedule`;
   - `generateSlots`;
   - `setSlotStatus`;
   - `listScheduleSlots` nếu Backend bổ sung read endpoint.
2. Thêm dialog tạo schedule:
   - ngày/giờ bắt đầu;
   - ngày/giờ kết thúc;
   - timezone rõ ràng;
   - thời lượng slot.
3. Sau khi tạo, cho phép bấm **Sinh slot**; nếu generation lỗi, schedule vẫn hiển thị và có thể retry.
4. Cho sửa interval/duration khi chưa có slot.
5. Khi đã có slot, không cho sửa interval; cho hủy schedule theo Backend rule.
6. Hiển thị và block/unblock slot phù hợp; không cho thay đổi slot `BOOKED`.
7. Invalidate schedule và available-slot queries sau mutation.
8. Hiển thị loading/error/empty/success và conflict rõ ràng.

#### Backend tối thiểu cần mở rộng

Để quản lý lại cả slot `BLOCKED` sau reload, bổ sung read endpoint có kiểm soát:

```http
GET /api/v1/schedules/{schedule_id}/slots
```

Endpoint trả toàn bộ slot của schedule cho Doctor sở hữu hoặc Staff/Admin. Public/Patient vẫn dùng `/available-slots` và chỉ thấy slot phù hợp.

Không tạo migration vì schema không đổi.

#### Demo data

Có thể mở rộng seed synthetic để schedule demo có đủ các slot của khoảng 2 giờ, giữ một slot BOOKED và các slot còn lại AVAILABLE. Đây chỉ là dữ liệu demo; không thay thế việc hoàn thiện UI quản lý schedule.

Nên tránh seed phụ thuộc cứng vào ngày gần hiện tại. Nếu cần lịch luôn dùng được trong demo, tạo script provisioning lịch demo tương lai có kiểm soát và idempotent thay vì tự sinh dữ liệu mỗi lần Backend khởi động.

### Test bắt buộc

#### Backend

- Doctor tạo schedule của chính mình.
- Doctor không tạo schedule cho Doctor khác.
- Staff/Admin theo quyền tạo/cập nhật được.
- Past/invalid/divisibility/overlap bị từ chối.
- Concurrent overlap vẫn chỉ một workflow commit.
- Generate đúng số slot; generate lần hai bị conflict.
- List all slots yêu cầu đúng quyền.
- Block/unblock AVAILABLE/BLOCKED; BOOKED bị từ chối.
- Cancel schedule block các slot AVAILABLE theo rule hiện có.

#### Frontend

- Create form validation và timezone.
- Tạo schedule thành công.
- Overlap/business error hiển thị đúng.
- Generate slots và Patient thấy slot AVAILABLE.
- Không cho sửa interval khi đã có slot.
- Block/unblock và BOOKED protection.
- Loading/error/empty/success.
- Query invalidation đúng, không reload toàn app.

#### End-to-end

```text
Doctor login
→ tạo schedule tương lai
→ sinh slot
→ Patient login
→ chọn Doctor
→ thấy slot AVAILABLE
→ booking
→ slot BOOKED
```

Chạy lại Backend full regression, Frontend test/lint/build và Playwright/relevant Business MVP E2E trước khi đánh dấu DONE.

### Trạng thái

**OPEN — NOT IMPLEMENTED.**

---

## Quy tắc cập nhật tracker

Khi bắt đầu sửa một issue:

1. Chuyển trạng thái sang `IN PROGRESS`.
2. Ghi files tạo/sửa và xác nhận có migration hay không.
3. Sau implementation, chuyển `VERIFYING` và ghi test command/kết quả thật.
4. Chỉ chuyển `DONE` khi tất cả acceptance/test bắt buộc PASS.
5. Đồng bộ `phase-14.md`, `requirement-traceability.md`, test matrix và demo script nếu hành vi demo thay đổi.

