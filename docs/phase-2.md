# Phase 2 — Database Design + ERD + pgvector + MedicalRecord

Ngày thực hiện: 19/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

Baseline đã xác minh: **SRS v1.1 Final**, bao gồm FR-MR-01..06, BR-21..24, UC-12/13 và các NFR/AC/DR liên quan MedicalRecord.

## Kết quả

- Tạo 14 SQLAlchemy 2 models/tables: users, roles, user_roles, refresh_sessions, specialties, doctors, doctor_schedules, schedule_slots, appointments, medical_records, documents, document_chunks, handoff_requests, audit_logs.
- Không tạo ChatSession vì requirement hiện tại là Should và không cần cho phạm vi database bắt buộc.
- Tạo migration `0002_create_business_schema` nối tiếp `0001_enable_pgvector`; không sửa migration 0001.
- Tạo `VECTOR(1024)` cho BGE-M3, HNSW cosine index, document/chunk FK và unique chunk order.
- Tạo partial unique index chống tái sử dụng slot đang CONFIRMED hoặc đã kết thúc bằng COMPLETED/NO_SHOW; chỉ CANCELLED có thể giải phóng slot theo BR-04.
- Tạo Appointment `1:0..1` MedicalRecord bằng FK + UNIQUE; không duplicate doctor/patient/specialty và không có thiết kế hard-delete.
- Tạo seed idempotent chỉ gồm dữ liệu synthetic: bốn role, ba specialty, doctor/patient/staff demo, schedules/slots, một Appointment COMPLETED có MedicalRecord, một Appointment CONFIRMED và audit metadata không chứa nội dung khám.
- Hoàn thiện ERD và Data Dictionary toàn bộ schema.

## Kiểm chứng

| Hạng mục | Kết quả |
| --- | --- |
| PostgreSQL / pgvector | PostgreSQL 18.6, pgvector 0.8.7 |
| Migration round-trip | 0002 → 0003 → 0002 → 0003 thành công; dữ liệu seed được giữ |
| Model/schema parity | `alembic check`: không có operation mới |
| Seed idempotency | Chạy hai lần thành công, không tạo trùng |
| Unit + integration | `RUN_DB_INTEGRATION=1`: 28/28 tests pass sau final audit |
| Vector | Insert/search cosine với đúng 1024 chiều |
| MedicalRecord | FK orphan bị chặn; appointment_id unique bị chặn; sample chỉ gắn Appointment COMPLETED |
| Appointment | Hai CONFIRMED cùng slot bị partial unique index chặn |
| Transaction | Bản ghi test rollback không tồn tại sau transaction |

## Ranh giới chưa triển khai

- Không có API CRUD, service nghiệp vụ hay UI mới: đó là Phase 3/4.
- Quyền Doctor/Patient/Staff/Admin, JWT/refresh rotation thực tế và Argon2 là Phase 5.
- Kiểm tra schedule overlap liên hàng (có khóa theo doctor để tránh race), khóa slot khi đặt lịch và kiểm tra MedicalRecord chỉ do đúng Doctor tạo trên Appointment COMPLETED phải nằm trong transaction ở service Phase 3/6.
- Không ingest tài liệu, không gọi BGE-M3/Gemini, không triển khai RAG/Tool Calling.
- Không đơn thuốc, xét nghiệm, file đính kèm bệnh án, HIS/EMR; MedicalRecord không liên kết RAG.
- HNSW được tạo sẵn ở mức lưu trữ; BM25/RRF/reranker vẫn thuộc roadmap RAG V2/V3.

## Checklist Done

- [x] ERD hoàn chỉnh
- [x] Data Dictionary đầy đủ
- [x] SQLAlchemy 2 models nhất quán
- [x] Migration mới sau 0001, upgrade/downgrade pass
- [x] MedicalRecord 1:0..1 Appointment
- [x] Vector schema BGE-M3 1024 chiều phù hợp
- [x] Seed synthetic và nhất quán
- [x] Constraint/integration tests
- [x] Không chuyển sang Phase 3
