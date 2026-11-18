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
| ISSUE-001 | Admin phải nhập trực tiếp User UUID khi tạo Doctor profile | UX/Frontend–Backend integration gap | Medium | DONE — 06/11/2026 |
| ISSUE-002 | Doctor không thể tạo/sửa/sinh slot trên UI; Patient không thấy lịch trống | Business workflow/Frontend integration gap | High cho demo | DONE — 06/11/2026 |
| ENH-001 | Admin tạo đồng thời tài khoản User role DOCTOR và Doctor profile | Workflow extension được người dùng chốt | Medium | DONE — 06/11/2026 |

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

Sau khi xem xét phương án, người dùng đã quyết định bổ sung luôn luồng Admin tạo tài khoản Doctor mới và Doctor profile trong cùng Dialog. Phần mở rộng này dùng schema hiện có, không cần bảng hoặc migration mới.

### Phương án đã chốt

Chi tiết đầy đủ nằm trong `doctor-user-selection-fix-plan.md`.

Tóm tắt:

1. Đã thêm `GET /api/v1/doctors/candidates`, chỉ Admin.
2. Chỉ trả User `ACTIVE`, có role `DOCTOR`, chưa có Doctor profile.
3. Response chỉ chứa `id`, `full_name`, `email`, `phone` cần thiết.
4. Đã bỏ ô UUID và dùng dropdown `Họ tên — email` khi liên kết tài khoản có sẵn.
5. Dialog mặc định cho phép tạo đồng thời User role `DOCTOR` và Doctor profile qua `POST /api/v1/doctors/provision`.
6. Provisioning chạy trong một transaction, dùng Argon2, audit không chứa mật khẩu và rollback nếu có lỗi.
7. Giữ validation Backend authoritative; invalidate Doctor list và candidate query sau mutation.
8. Không tạo migration, service/router/model trùng.

### Test bắt buộc

- Admin xem candidates; Patient/Doctor/Staff bị 403.
- Loại User sai role, inactive hoặc đã có profile.
- Dropdown loading/error/empty/success.
- Không nhập UUID thủ công.
- Submit đúng `user_id`; duplicate/race trả 409 rõ ràng.
- Backend full regression; Frontend test/lint/build; Playwright smoke.

### Trạng thái

**DONE — 06/11/2026.**

Implementation chính: `app/doctors/{schemas,repository,service,router}.py`, `src/features/doctors/{api,DoctorAdminPage}.tsx` và `src/types/domain.ts`.

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

Frontend trước khi sửa chỉ có:

- `GET /schedules`.
- `GET /schedules/available-slots`.
- Màn hình read-only hiển thị schedule và slot AVAILABLE.

### Nguyên nhân

ScheduleService và API mutation đã được triển khai, nhưng Frontend Phase 4 chỉ nối luồng xem. Dữ liệu seed chỉ tạo một slot cho mỗi schedule và cả hai slot đều BOOKED, nên không có dữ liệu AVAILABLE che lấp khoảng trống UI này.

### Phân loại phạm vi

Đây là business workflow/Frontend integration gap có mức độ **High cho demo**, vì chặn luồng Patient tìm slot và Doctor tự chuẩn bị lịch.

Phải reuse `ScheduleService`, repository, router và database hiện có; không được viết lại concurrency/overlap logic.

### Phương án đã triển khai

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

**DONE — 06/11/2026.**

Doctor có thể tạo lịch tương lai, sửa lịch chưa có slot, hủy lịch, sinh slot và block/unblock slot phù hợp ngay trên UI. Backend được mở rộng tối thiểu bằng endpoint bảo vệ `GET /api/v1/schedules/{schedule_id}/slots`; toàn bộ overlap lock, ownership và business rules hiện có tiếp tục được reuse.

## Bằng chứng kiểm thử sau khi sửa

| Gate | Kết quả |
| --- | --- |
| Backend test tập trung Doctor/Schedule/HTTP contract | **12/12 PASS** |
| Backend full regression với PostgreSQL thật | **162/162 PASS** |
| Frontend workflow tests mới | **4/4 PASS** |
| Frontend full regression | **41/41 PASS** (8 files) |
| Frontend ESLint | **PASS**, 0 warning |
| Frontend production build | **PASS**, largest JS khoảng 398.03 kB |

Không có thay đổi schema và không tạo migration mới. Các integration test dùng savepoint/rollback, không để lại dữ liệu thử trong database demo.

## Post-Phase-14 workflow verification — 06/11/2026

- ISSUE-001: **VERIFIED DONE** bằng browser — Admin link candidate bằng tên/email, không raw UUID; candidate biến mất sau create.
- ENH-001: **VERIFIED DONE** bằng browser + PostgreSQL — provision Doctor, login thật, Argon2, role/profile/audit đúng.
- ISSUE-002: **VERIFIED DONE** bằng browser — create/update Schedule, generate/block slot, Patient discovery/booking.
- Business Golden Path: **PASS**; Business Workflow Readiness: **READY**.
- Hai gap UI mới `POST14-WF-01/02` được sửa tối thiểu và regression PASS; chi tiết trong `post-phase14-business-workflow-verification.md`.
- Final gates: Backend 162/162; Frontend 41/41; Playwright 4/4; lint/build/Alembic PASS.

---

## Quy tắc cập nhật tracker

Khi bắt đầu sửa một issue:

1. Chuyển trạng thái sang `IN PROGRESS`.
2. Ghi files tạo/sửa và xác nhận có migration hay không.
3. Sau implementation, chuyển `VERIFYING` và ghi test command/kết quả thật.
4. Chỉ chuyển `DONE` khi tất cả acceptance/test bắt buộc PASS.
5. Đồng bộ `phase-14.md`, `requirement-traceability.md`, test matrix và demo script nếu hành vi demo thay đổi.

