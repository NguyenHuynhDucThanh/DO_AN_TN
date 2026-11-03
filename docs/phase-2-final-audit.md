# Phase 2 Final Audit

Ngày audit: 19/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

Kết luận: **PHASE 2 FINAL AUDIT: PASS.** Hai sai lệch schema phát hiện trong audit đã được sửa bằng migration mới `0003_phase2_invariants`; không sửa lịch sử migration 0001/0002 và không triển khai Phase 3.

| # | Điểm kiểm tra | Kết quả | Bằng chứng | Hành động |
| --- | --- | --- | --- | --- |
| 1 | Patient phone nullable | DEFERRED TO PHASE 5 | `users.phone` nullable trên DB thật; FR-AUTH-01 yêu cầu phone cho đăng ký Patient nhưng User dùng chung bốn role. | Giữ nullable; Phase 5 bắt buộc phone trong Patient registration schema/service và thêm test thiếu/sai phone. |
| 2 | Appointment partial unique index | PASS | DB có `uq_appointments_occupied_slot` cho CONFIRMED/COMPLETED/NO_SHOW; test chặn đặt lại slot COMPLETED và cho tái đặt sau CANCELLED. | Migration 0003 thay index cũ chỉ lọc CONFIRMED. Phase 6 cập nhật Appointment + Slot trong cùng transaction. |
| 3 | Cascade/delete history | PASS | Schedule→Slot CASCADE bị Appointment→Slot RESTRICT chặn nếu đã có lịch; MedicalRecord→Appointment RESTRICT; Doctor→Schedule RESTRICT. Test FK/orphan pass. | Giữ schema; service dùng trạng thái thay hard-delete. DocumentChunk CASCADE và session/user-role CASCADE chỉ dành dữ liệu kỹ thuật. |
| 4 | Schedule overlap | DEFERRED TO PHASE 3/6 | Exact-range unique không chặn 08:00–10:00 với 09:00–11:00; chưa có `btree_gist`. | Schedule service khóa theo doctor trong transaction, truy vấn overlap và test race condition/adjacent ranges. Không thêm extension mới ở Phase 2. |
| 5 | HNSW/exact baseline | DEFERRED TO PHASE 8/12 | HNSW cosine tồn tại và planner có thể chọn cho ORDER BY distance + LIMIT. pgvector quy định index HNSW là approximate. | Phase 8 dùng `SET LOCAL enable_indexscan=off` + EXPLAIN để lấy exact baseline; Phase 12 bật HNSW và so latency/recall trên cùng query set. |
| 6 | Handoff role/status | DEFERRED TO PHASE 5/9 | SRS chỉ Staff/Admin xử lý và chỉ có PENDING/IN_PROGRESS/RESOLVED. DB CHECK 0003 loại CANCELLED; docs không còn ghi Doctor. FK chỉ kiểm tra User tồn tại. | RBAC service Phase 5/9 kiểm tra assigned user có STAFF/ADMIN; thêm authorization/state-transition tests. |
| 7 | MedicalRecord integrity | PASS | `appointment_id` FK+UNIQUE; không doctor_id/patient_id/specialty_id; ON DELETE RESTRICT; không FK/vector tới documents; audit seed chỉ có metadata. Tests orphan/duplicate/completed sample pass. | Phase 3/5/6 kiểm tra Appointment COMPLETED, Doctor phụ trách và quyền Patient/Doctor trong transaction; test NFR-TEST-02. |
| 8 | BGE-M3 dimension | PASS | Nguồn BAAI/FlagEmbedding công bố 1024; model constant, Alembic và PostgreSQL đều `VECTOR(1024)`; insert/cosine test dùng 1024 phần tử. | Không đổi dimension. |
| 9 | Migration chain | PASS | Một head: 0001 → 0002 → 0003. `current`, `heads`, `check` pass; 0003 downgrade về 0002 rồi upgrade lại thành công. | Giữ 0001/0002 bất biến; mọi sửa tiếp theo dùng migration mới. |
| 10 | Model/Migration/DB parity | PASS | Audit trực tiếp columns/types/nullability/FK/UNIQUE/CHECK/index/partial index/vector/HNSW/ON DELETE; `alembic check` không có operation mới. 0003 bổ sung CHECK enum còn thiếu trong DB. | Duy trì integration tests và kiểm tra schema ở mỗi migration. |

## Các sửa đổi từ audit

- `app/models/enums.py`: bỏ Handoff `CANCELLED` không có trong SRS.
- `app/models/care.py`: đổi partial unique index sang ba trạng thái chiếm slot.
- `app/models/knowledge.py`: thêm CHECK loại file và chỉ ingest sau APPROVED.
- `migrations/versions/0003_strengthen_phase2_invariants.py`: migration mới cho index và CHECK; không sửa 0002 đã apply.
- `tests/test_phase2_models.py`, `tests/test_phase2_database_integration.py`, `tests/test_database_integration.py`: kiểm tra index mới, terminal slot, rebook sau CANCELLED, Handoff state và revision.
- `database-design.md`, `data-dictionary.md`, `requirement-traceability.md`, README: đồng bộ quyết định và các phase deferred.

## Checklist

- [x] Không mất dữ liệu lịch sử Appointment
- [x] Không mất MedicalRecord do cascade sai
- [x] Double booking được bảo vệ hợp lý
- [x] Schedule overlap có chiến lược rõ
- [x] Patient phone requirement được mapping rõ
- [x] Handoff role/status khớp SRS
- [x] MedicalRecord privacy/integrity đúng
- [x] VECTOR(1024) đã xác minh
- [x] RAG exact/HNSW strategy rõ
- [x] Alembic migration chain sạch
- [x] Tests PASS
