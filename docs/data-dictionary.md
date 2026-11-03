# Data Dictionary — Phase 2

Quy ước: `PK` khóa chính, `FK` khóa ngoại, `UK` unique; UUID PK mặc định `gen_random_uuid()`, `created_at/updated_at` mặc định `now()` nếu không ghi khác.

## Identity và Authorization

| Table | Column | Type | Nullable | Default | PK | FK | Unique | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| users | id | UUID | No | generated | Yes | — | Yes | Định danh người dùng. |
| users | email | VARCHAR(320) | No | — | No | — | lower(email) | Email đăng nhập, không phân biệt hoa/thường. |
| users | password_hash | VARCHAR(255) | No | — | No | — | No | Chỉ lưu password hash; seed dùng sentinel không đăng nhập được. |
| users | full_name | VARCHAR(150) | No | — | No | — | No | Họ tên hiển thị. |
| users | phone | VARCHAR(20) | Yes | NULL | No | — | No | Nullable cho User dùng chung; Patient registration Phase 5 bắt buộc validate theo FR-AUTH-01. |
| users | date_of_birth | DATE | Yes | NULL | No | — | No | Ngày sinh. |
| users | gender | VARCHAR(16) | Yes | NULL | No | — | No | FEMALE/MALE/OTHER/UNDISCLOSED. |
| users | status | VARCHAR(16) | No | ACTIVE | No | — | No | ACTIVE/INACTIVE/LOCKED. |
| users | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| users | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| roles | id | UUID | No | generated | Yes | — | Yes | Định danh vai trò. |
| roles | code | VARCHAR(20) | No | — | No | — | Yes | PATIENT/DOCTOR/STAFF/ADMIN. |
| roles | name | VARCHAR(80) | No | — | No | — | No | Tên vai trò. |
| roles | description | VARCHAR(255) | Yes | NULL | No | — | No | Mô tả. |
| roles | is_active | BOOLEAN | No | true | No | — | No | Cho phép sử dụng vai trò. |
| roles | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| roles | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| user_roles | user_id | UUID | No | — | Yes | users.id | Pair | Người được gán. |
| user_roles | role_id | UUID | No | — | Yes | roles.id | Pair | Vai trò được gán. |
| user_roles | assigned_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm gán. |
| user_roles | assigned_by | UUID | Yes | NULL | No | users.id | No | Người thực hiện; SET NULL nếu tài khoản mất. |
| refresh_sessions | id | UUID | No | generated | Yes | — | Yes | Phiên refresh token. |
| refresh_sessions | user_id | UUID | No | — | No | users.id | No | Chủ phiên. |
| refresh_sessions | family_id | UUID | No | generated | No | — | No | Nhóm token trong chuỗi rotation. |
| refresh_sessions | token_hash | VARCHAR(64) | No | — | No | — | Yes | SHA-256/giá trị hash, không lưu token thô. |
| refresh_sessions | expires_at | TIMESTAMPTZ | No | — | No | — | No | Hết hạn. |
| refresh_sessions | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm phát hành. |
| refresh_sessions | last_used_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Lần dùng gần nhất. |
| refresh_sessions | revoked_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Thời điểm thu hồi. |
| refresh_sessions | replaced_by_session_id | UUID | Yes | NULL | No | refresh_sessions.id | No | Token thay thế sau rotation. |
| refresh_sessions | user_agent | VARCHAR(500) | Yes | NULL | No | — | No | Metadata thiết bị. |
| refresh_sessions | ip_address | VARCHAR(45) | Yes | NULL | No | — | No | IPv4/IPv6 quan sát được. |

## Chuyên khoa, bác sĩ và lịch

| Table | Column | Type | Nullable | Default | PK | FK | Unique | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| specialties | id | UUID | No | generated | Yes | — | Yes | Định danh chuyên khoa. |
| specialties | code | VARCHAR(30) | No | — | No | — | Yes | Mã ổn định. |
| specialties | name | VARCHAR(120) | No | — | No | — | Yes | Tên chuyên khoa. |
| specialties | description | TEXT | Yes | NULL | No | — | No | Mô tả. |
| specialties | is_active | BOOLEAN | No | true | No | — | No | Trạng thái sử dụng. |
| specialties | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| specialties | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| doctors | id | UUID | No | generated | Yes | — | Yes | Định danh hồ sơ bác sĩ. |
| doctors | user_id | UUID | No | — | No | users.id | Yes | Tài khoản gắn một hồ sơ bác sĩ. |
| doctors | specialty_id | UUID | No | — | No | specialties.id | No | Chuyên khoa chính trong MVP. |
| doctors | license_number | VARCHAR(50) | No | — | No | — | Yes | Mã hành nghề/demo identifier. |
| doctors | biography | TEXT | Yes | NULL | No | — | No | Giới thiệu công khai. |
| doctors | is_active | BOOLEAN | No | true | No | — | No | Bác sĩ còn hoạt động. |
| doctors | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| doctors | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| doctor_schedules | id | UUID | No | generated | Yes | — | Yes | Khung làm việc. |
| doctor_schedules | doctor_id | UUID | No | — | No | doctors.id | Range | Bác sĩ; cùng range không lặp. |
| doctor_schedules | start_at | TIMESTAMPTZ | No | — | No | — | Range | Bắt đầu; nhỏ hơn end_at. |
| doctor_schedules | end_at | TIMESTAMPTZ | No | — | No | — | Range | Kết thúc. |
| doctor_schedules | slot_duration_minutes | INTEGER | No | — | No | — | No | 5–480 phút. |
| doctor_schedules | status | VARCHAR(16) | No | ACTIVE | No | — | No | ACTIVE/CANCELLED. |
| doctor_schedules | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| doctor_schedules | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| schedule_slots | id | UUID | No | generated | Yes | — | Yes | Slot đặt lịch. |
| schedule_slots | schedule_id | UUID | No | — | No | doctor_schedules.id | Pair | Schedule cha; cascade xóa kỹ thuật. |
| schedule_slots | start_at | TIMESTAMPTZ | No | — | No | — | Pair | Bắt đầu duy nhất trong schedule. |
| schedule_slots | end_at | TIMESTAMPTZ | No | — | No | — | No | Kết thúc, lớn hơn start_at. |
| schedule_slots | status | VARCHAR(16) | No | AVAILABLE | No | — | No | AVAILABLE/BOOKED/BLOCKED. |
| schedule_slots | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| schedule_slots | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |

## Appointment và MedicalRecord

| Table | Column | Type | Nullable | Default | PK | FK | Unique | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| appointments | id | UUID | No | generated | Yes | — | Yes | Định danh lịch hẹn. |
| appointments | patient_id | UUID | No | — | No | users.id | No | Người bệnh đặt lịch. |
| appointments | schedule_slot_id | UUID | No | — | No | schedule_slots.id | Partial | Unique khi status thuộc CONFIRMED/COMPLETED/NO_SHOW; CANCELLED cho phép tái đặt theo BR-04. |
| appointments | status | VARCHAR(16) | No | CONFIRMED | No | — | No | CONFIRMED/CANCELLED/COMPLETED/NO_SHOW. |
| appointments | booked_at | TIMESTAMPTZ | No | — | No | — | No | Thời điểm đặt. |
| appointments | cancelled_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Bắt buộc khi CANCELLED. |
| appointments | cancelled_by | UUID | Yes | NULL | No | users.id | No | Người hủy. |
| appointments | cancellation_reason | VARCHAR(500) | Yes | NULL | No | — | No | Lý do hủy. |
| appointments | completed_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Bắt buộc khi COMPLETED. |
| appointments | no_show_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Bắt buộc khi NO_SHOW. |
| appointments | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| appointments | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| medical_records | id | UUID | No | generated | Yes | — | Yes | Định danh hồ sơ khám cơ bản. |
| medical_records | appointment_id | UUID | No | — | No | appointments.id | Yes | Tối đa một hồ sơ mỗi Appointment. |
| medical_records | symptoms | TEXT | No | — | No | — | No | Triệu chứng bác sĩ ghi nhận. |
| medical_records | clinical_notes | TEXT | No | — | No | — | No | Ghi chú khám. |
| medical_records | doctor_conclusion | TEXT | No | — | No | — | No | Kết luận do Doctor nhập, không phải AI. |
| medical_records | follow_up_instructions | TEXT | No | — | No | — | No | Hướng dẫn sau khám. |
| medical_records | created_by | UUID | No | — | No | users.id | No | Doctor tạo. |
| medical_records | updated_by | UUID | No | — | No | users.id | No | Doctor cập nhật gần nhất. |
| medical_records | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| medical_records | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |

## Knowledge base / RAG

| Table | Column | Type | Nullable | Default | PK | FK | Unique | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| documents | id | UUID | No | generated | Yes | — | Yes | Phiên bản tài liệu nguồn. |
| documents | title | VARCHAR(255) | No | — | No | — | No | Tiêu đề. |
| documents | file_name | VARCHAR(255) | No | — | No | — | No | Tên file an toàn. |
| documents | file_type | VARCHAR(10) | No | — | No | — | No | JSON/CSV/PDF/DOCX; CHECK được mở rộng bởi migration 0004. |
| documents | storage_key | VARCHAR(500) | No | — | No | — | No | Khóa/path lưu file, không phải nội dung. |
| documents | source_name | VARCHAR(255) | Yes | NULL | No | — | No | Tổ chức/nguồn. |
| documents | source_url | VARCHAR(1000) | Yes | NULL | No | — | No | URL tham chiếu nguồn. |
| documents | checksum_sha256 | VARCHAR(64) | No | — | No | — | Pair | Checksum; unique cùng version. |
| documents | version_number | INTEGER | No | 1 | No | — | Pair | Phiên bản dương. |
| documents | approval_status | VARCHAR(16) | No | PENDING | No | — | No | PENDING/APPROVED/REJECTED. |
| documents | ingestion_status | VARCHAR(20) | No | NOT_INGESTED | No | — | No | NOT_INGESTED/PROCESSING/COMPLETED/FAILED. |
| documents | uploaded_by | UUID | No | — | No | users.id | No | Người tải lên. |
| documents | approved_by | UUID | Yes | NULL | No | users.id | No | Người duyệt. |
| documents | approved_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Thời điểm duyệt. |
| documents | ingestion_error | VARCHAR(1000) | Yes | NULL | No | — | No | Thông báo lỗi kỹ thuật đã lọc. |
| documents | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| documents | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| document_chunks | id | UUID | No | generated | Yes | — | Yes | Định danh chunk. |
| document_chunks | document_id | UUID | No | — | No | documents.id | Pair | Document cha; cascade khi re-ingest/xóa kỹ thuật. |
| document_chunks | chunk_index | INTEGER | No | — | No | — | Pair | Chỉ số từ 0, unique trong document. |
| document_chunks | content | TEXT | No | — | No | — | Nội dung chuẩn hóa của chunk. |
| document_chunks | embedding | VECTOR(1024) | No | — | No | — | No | Dense embedding BGE-M3; HNSW cosine index. |
| document_chunks | page_number | INTEGER | Yes | NULL | No | — | No | Trang nguồn, nếu có; phải dương. |
| document_chunks | section | VARCHAR(255) | Yes | NULL | No | — | No | Đề mục nguồn. |
| document_chunks | metadata | JSONB | No | {} | No | — | No | Metadata retrieval không chứa MedicalRecord. |
| document_chunks | content_hash | VARCHAR(64) | No | — | No | — | No | Hash nội dung chunk. |
| document_chunks | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm ingest. |

## Handoff và Audit

| Table | Column | Type | Nullable | Default | PK | FK | Unique | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| handoff_requests | id | UUID | No | generated | Yes | — | Yes | Yêu cầu chuyển nhân viên. |
| handoff_requests | requester_id | UUID | No | — | No | users.id | No | Người yêu cầu. |
| handoff_requests | assigned_to | UUID | Yes | NULL | No | users.id | No | Staff/Admin được phân công; role do RBAC service kiểm tra. |
| handoff_requests | source | VARCHAR(30) | No | CHATBOT | No | — | No | Nguồn tạo yêu cầu. |
| handoff_requests | reason | TEXT | No | — | No | — | No | Lý do chuyển, không dùng làm hồ sơ lâm sàng. |
| handoff_requests | priority | VARCHAR(16) | No | NORMAL | No | — | No | NORMAL/HIGH/URGENT. |
| handoff_requests | status | VARCHAR(16) | No | PENDING | No | — | No | PENDING/IN_PROGRESS/RESOLVED theo SRS v1.1. |
| handoff_requests | resolved_at | TIMESTAMPTZ | Yes | NULL | No | — | No | Thời điểm xử lý xong. |
| handoff_requests | created_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm tạo. |
| handoff_requests | updated_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm cập nhật. |
| audit_logs | id | BIGINT | No | identity/serial | Yes | — | Yes | Định danh log. |
| audit_logs | actor_user_id | UUID | Yes | NULL | No | users.id | No | Chủ thể; SET NULL khi tài khoản mất. |
| audit_logs | action | VARCHAR(80) | No | — | No | — | No | Ví dụ MEDICAL_RECORD_UPDATED. |
| audit_logs | entity_type | VARCHAR(80) | No | — | No | — | Pair index | Loại thực thể. |
| audit_logs | entity_id | UUID | Yes | NULL | No | — | Pair index | ID thực thể, không FK đa hình. |
| audit_logs | request_id | UUID | Yes | NULL | No | — | No | Correlation ID. |
| audit_logs | metadata | JSONB | No | {} | No | — | No | Chỉ metadata; cấm triệu chứng/ghi chú/kết luận. |
| audit_logs | occurred_at | TIMESTAMPTZ | No | now() | No | — | No | Thời điểm sự kiện. |
