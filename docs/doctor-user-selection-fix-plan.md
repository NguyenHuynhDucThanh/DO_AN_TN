# Kế hoạch sửa luồng chọn User khi tạo Doctor Profile

Ngày ghi nhận: 03/11/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

## 1. Vấn đề hiện tại

Màn hình Admin → Quản lý bác sĩ → Thêm hồ sơ bác sĩ yêu cầu nhập trực tiếp `User UUID`.

Backend đang áp dụng đúng mô hình dữ liệu:

- Doctor profile phải liên kết với một `User` tồn tại.
- User đó phải có role `DOCTOR`.
- Một User chỉ có tối đa một Doctor profile.
- Chỉ Admin được tạo Doctor master data.

Tuy nhiên Frontend không có danh sách User phù hợp để Admin lựa chọn và hệ thống cũng chưa có API phục vụ danh sách này. Admin thông thường không thể biết UUID, dễ nhập sai hoặc cố tạo lại Doctor profile đã tồn tại.

Đây là **UX/integration gap trong chức năng Doctor management đã có**, không phải lý do để viết lại Auth, DoctorService hoặc database.

## 2. Phân loại thay đổi

**Loại:** bug/UX fix bắt buộc sau Phase 14.

Phạm vi fix này chỉ thay ô nhập UUID bằng lựa chọn có kiểm soát từ dữ liệu thật. Nó không bổ sung nghiệp vụ mới và không thay SRS.

Việc cho Admin tạo hoàn toàn một tài khoản Doctor mới, đặt mật khẩu hoặc gửi lời mời kích hoạt là chức năng khác. Nếu cần thực hiện sau này, phải có Change Request riêng vì liên quan provisioning, password lifecycle và security.

## 3. Giải pháp được chọn

```text
Admin mở form thêm Doctor
→ Frontend gọi API lấy Doctor candidates
→ Backend xác thực Admin
→ PostgreSQL trả User ACTIVE có role DOCTOR
  và chưa có Doctor profile
→ Frontend hiển thị dropdown: Họ tên + email
→ Admin chọn User, Specialty, nhập license/biography
→ POST /doctors dùng user_id đã chọn
→ DoctorService hiện có xác thực lại role/reference/unique
→ Tạo Doctor profile
```

Backend vẫn là nguồn quyết định cuối cùng. Frontend dropdown chỉ cải thiện UX, không thay thế validation trong `DoctorService.create()`.

## 4. Backend plan

### 4.1 Endpoint mới tối thiểu

Đề xuất:

```http
GET /api/v1/doctors/candidates
```

Quyền truy cập: chỉ `ADMIN`.

Response tối thiểu:

```json
[
  {
    "id": "user-uuid",
    "full_name": "Tên bác sĩ",
    "email": "doctor@example.invalid",
    "phone": "..."
  }
]
```

Endpoint phải được khai báo trước route động `/doctors/{doctor_id}` để `candidates` không bị parse như UUID.

### 4.2 Query candidate

Chỉ trả User thỏa tất cả điều kiện:

- `users.status = ACTIVE`;
- có role `DOCTOR`;
- chưa có bản ghi trong `doctors` theo `doctors.user_id`;
- sắp xếp ổn định theo `full_name`, sau đó `email`.

Không trả password hash, refresh session, role nội bộ không cần thiết hoặc dữ liệu nhạy cảm.

### 4.3 Kiến trúc reuse

- Mở rộng `DoctorRepository` bằng query candidate.
- Mở rộng `DoctorService` bằng `list_candidates(actor)` và `actor.require_any_role("ADMIN")`.
- Mở rộng Doctor router/schema hiện có.
- Giữ nguyên `DoctorService.create()` để kiểm tra lại User, role, Specialty và unique constraint khi submit.
- Không tạo module/service/router Doctor thứ hai.
- Không tạo migration vì schema không thay đổi.
- Không sửa AuthService, User model, Doctor model hoặc migration đã apply.

## 5. Frontend plan

### 5.1 API và query

- Thêm `listDoctorCandidates()` trong feature `doctors/api.ts`.
- Dùng TanStack Query với key riêng, ví dụ `doctorKeys.candidates`.
- Chỉ fetch khi dialog tạo mới được mở hoặc theo cơ chế query hợp lý hiện có.
- Sau khi tạo Doctor thành công, invalidate cả `doctorKeys.all` và candidate query.

### 5.2 Form

- Xóa `TextField` nhập tự do `User UUID` khỏi create form.
- Thay bằng MUI Select/Autocomplete hiển thị:

```text
Họ tên — email
```

- Giá trị gửi Backend vẫn là `user_id` UUID.
- Khi chỉnh sửa Doctor hiện có, không cho đổi `user_id`.
- Giữ các trường Specialty, license number, biography và trạng thái hiện tại.

### 5.3 UX states

Form candidate phải có:

- loading;
- API error;
- empty state: “Không có tài khoản Doctor chưa được gắn hồ sơ”;
- success;
- validation khi chưa chọn User;
- conflict 409 nếu candidate vừa được Admin khác sử dụng.

Nếu candidate list rỗng:

- disable thao tác lưu/tạo;
- hướng dẫn chạy seed/script provisioning User Doctor;
- không yêu cầu Admin tự tìm UUID.

## 6. Provisioning User Doctor ngoài phạm vi fix

Fix này không tạo tài khoản Doctor mới. User Doctor vẫn được chuẩn bị bằng seed hoặc công cụ quản trị có kiểm soát.

Trong phạm vi đồ án/demo:

- có thể bổ sung một User Doctor synthetic chưa có profile vào seed để demo dropdown;
- password được đặt bằng prompt ẩn qua cơ chế hiện có;
- không hard-code password vào source, report hoặc Git.

Nếu muốn Admin tạo account Doctor trực tiếp trên UI, cần một Change Request riêng để quyết định:

- email/phone validation;
- initial password hay activation/invitation;
- role assignment audit;
- account ACTIVE/INACTIVE;
- reset/rotation password;
- notification và security policy.

## 7. Test plan

### Backend

- Admin lấy candidate list thành công.
- Patient/Doctor/Staff nhận 403.
- User không có role DOCTOR bị loại.
- User INACTIVE bị loại.
- User đã có Doctor profile bị loại.
- Candidate mới biến mất khỏi list sau khi tạo Doctor.
- Hai Admin chọn cùng candidate: chỉ một create thành công; request còn lại nhận 409.
- Response không chứa password hash/token/private credential.
- Regression Doctor CRUD/filter hiện có vẫn PASS.

### Frontend

- Create dialog tải candidate và hiển thị tên/email.
- Không còn ô nhập UUID thủ công.
- Loading/error/empty state hiển thị đúng.
- Không chọn candidate thì validation chặn submit.
- Submit gửi đúng `user_id` đã chọn.
- Tạo thành công invalidate Doctor list và candidates.
- Conflict 409 hiển thị thông báo dễ hiểu.
- Edit Doctor không cho thay User.

### Final regression bắt buộc

```powershell
# Backend
$env:RUN_DB_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest
Remove-Item Env:\RUN_DB_INTEGRATION

# Frontend
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

Playwright scoped smoke chỉ cần chạy lại nếu route/auth/API behavior dùng trong smoke bị ảnh hưởng; nên chạy lại trước khi chốt release để có bằng chứng đầy đủ.

## 8. Tiêu chí hoàn thành

- Admin không phải nhập hoặc sao chép UUID.
- Dropdown chỉ chứa User ACTIVE có role DOCTOR và chưa có Doctor profile.
- Backend tiếp tục validate role/reference/unique trong transaction hiện có.
- Không thể tạo hai Doctor profile cho cùng User.
- Không có migration mới.
- Không tạo service/router/model trùng.
- Không hard-code demo password.
- Backend/Frontend regression bắt buộc PASS.
- `phase-14.md`, requirement traceability và test matrix được cập nhật bằng kết quả thật sau khi triển khai.

## 9. Trạng thái

**PLANNED — NOT IMPLEMENTED.**

Không được đánh dấu DONE cho tới khi code và toàn bộ test bắt buộc đã chạy PASS.

