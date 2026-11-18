# Post-Phase-14 Full Business Workflow Verification

Ngày kiểm chứng: 06/11/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

Phạm vi: Business workflow độc lập AI. Không kiểm thử live Gemini, RAG, Tool Calling qua chatbot, Risk Alert, Voice/STT/TTS hoặc AI Handoff. Đây là verification/final stabilization, không phải Phase 15.

## A. Environment

| Hạng mục | Kết quả |
| --- | --- |
| Windows development / PostgreSQL | PASS |
| PostgreSQL / SQLAlchemy / pgvector | PostgreSQL 18.6; pgvector 0.8.7; cosine distance PASS |
| Migration | `0004_add_json_document_type` là current/head duy nhất |
| Schema drift | `alembic check`: no new upgrade operations |
| Backend/Frontend live | FastAPI `localhost:8013`; Vite `localhost:5174`; Edge qua Playwright |
| Dữ liệu | Chỉ synthetic `@example.invalid`; không dùng dữ liệu người bệnh thật |
| Auth | HttpOnly-cookie auth thật; `DEV_AUTH_ENABLED=false`; không dùng `X-Dev-User-Id` |

## B–R. Workflow verification

| Mục | Workflow | Kết quả | Evidence / giới hạn |
| --- | --- | --- | --- |
| B | Auth Patient | PASS | Register, cookie session, reload, logout, login lại; phone bắt buộc và localStorage không có access/refresh token. Duplicate/invalid/inactive tiếp tục được integration/component regression kiểm chứng. Không có Profile update UI nên phần đó N/A. |
| B | Auth Doctor/Staff/Admin | PASS | Cả ba role login/logout bằng cookie thật; route guard và session restore hoạt động. |
| C | Admin Specialty | PASS | UI create → edit → disable → enable; Specialty active xuất hiện trong Patient discovery mà không restart. |
| D | Admin link existing Doctor candidate | PASS | Fixture chỉ chuẩn bị User ACTIVE + role DOCTOR + chưa có profile; Admin chọn bằng tên/email, không thấy raw UUID, tạo profile thành công và candidate biến mất. Role/status filtering, race và 403 được Backend integration kiểm chứng. |
| E | Admin provision Doctor | PASS | UI tạo User + DOCTOR role + Doctor profile; Doctor xuất hiện sau invalidate/reload và đăng nhập được. PostgreSQL xác nhận Argon2, chỉ role DOCTOR, audit không chứa password. Rollback/duplicate được integration test kiểm chứng. |
| F | New Doctor login | PASS | Doctor mới login được; Doctor route mở; Admin route bị chặn. |
| G | Doctor Schedule | PASS | Tạo lịch tương lai, cập nhật interval trước khi có slot và reload giữ state. Cancel/overlap/past/divisibility/adjacent/unauthorized được service/integration regression kiểm chứng. |
| H | Slot management | PASS | Sinh đúng 3 slot, block 1, reload vẫn BLOCKED, còn 2 AVAILABLE; Patient chỉ thấy 2. Duplicate generation/BOOKED protection/RBAC được integration regression kiểm chứng. |
| I | Patient discovery | PASS | Chọn Specialty → Doctor mới → thấy đúng AVAILABLE slots; BLOCKED không xuất hiện. |
| J | Patient booking | PASS | UI booking tạo CONFIRMED, slot chuyển BOOKED và Appointment list cập nhật/reload đúng. |
| K | Cancel/Rebook | PASS | Patient hủy CONFIRMED → CANCELLED; reload đúng; slot được đặt lại qua UI và tạo một CONFIRMED mới. |
| L | Doctor Appointment | PASS | Doctor thấy Appointment được phân công và chuyển CONFIRMED → COMPLETED; invalid/other-doctor/NO_SHOW được integration regression kiểm chứng. |
| M | MedicalRecord Doctor | PASS | Sau COMPLETED, Doctor tạo đủ 4 trường, success state xuất hiện; reload chuyển sang update form. Completed-only, duplicate, ownership, no DELETE được integration regression kiểm chứng. |
| N | MedicalRecord Patient | PASS | Patient thấy record mới trong History, mở detail, reload vẫn tồn tại; không có nút edit/delete. |
| O | Staff/Admin privacy | PASS | Staff và Admin bị role guard chặn clinical detail UI; Backend privacy regression tiếp tục trả 403 theo policy. |
| P | Cross-role authorization | PASS | Live: Patient/Doctor/Staff/Admin route denials; Backend: unauthenticated, object ownership và clinical privacy regression. |
| Q | Query invalidation | PASS | Specialty, Doctor, Schedule, slot, booking, cancel, outcome và MedicalRecord đều cập nhật không cần full reload; reload sau đó vẫn khớp PostgreSQL. |
| R | Empty/error states | PASS WITH LIMITATION | Candidate empty/success và Doctor no-schedule được thấy live; 400/401/403/404/409/422/429, loading/error/empty coverage còn lại dựa trên component/integration regression, không kích hoạt từng lỗi trong golden browser run. |

## S. Database invariants

- Schedule advisory overlap lock và adjacent interval: PASS trong PostgreSQL integration.
- Concurrent booking: PASS; chỉ một transaction chiếm slot.
- `uq_appointments_occupied_slot`: PASS cho CONFIRMED/COMPLETED/NO_SHOW.
- Appointment 1:0..1 MedicalRecord: PASS.
- Provisioning User + role + Doctor: PASS transaction/rollback/audit tests.
- Live final state đọc lại từ PostgreSQL: Doctor password Argon2; role `DOCTOR`; Doctor profile tồn tại; Schedule `ACTIVE`; slots gồm `AVAILABLE`, `BLOCKED`, `BOOKED`; Appointment `COMPLETED`; MedicalRecord tồn tại; provisioning audit không có password.

## T. Seed audit

- Seed chỉ cung cấp role, Admin/Staff identity và dữ liệu demo nền.
- Golden path không dùng Doctor/Schedule/slot/Appointment/MedicalRecord seed để bỏ qua workflow.
- Doctor và Patient của golden path được tạo mới qua UI.
- Existing-candidate flow dùng fixture synthetic có kiểm soát chỉ để tạo precondition User DOCTOR chưa có profile; bước link profile thực hiện hoàn toàn qua UI.
- Các record `workflow.*@example.invalid` là dữ liệu synthetic verification và hiện được giữ lại làm evidence; không phải dữ liệu thật.
- Password của hai tài khoản demo `admin.demo@example.invalid` và `staff.demo@example.invalid` đã được đặt lại bằng `scripts/set_demo_password.py` để chạy cookie-auth E2E. Giá trị không được ghi vào source/report; trước buổi demo, người dùng nên chạy lại script bằng hidden prompt để chọn password riêng.

## U. Business Golden Path

```text
Admin login
→ create/edit/enable Specialty
→ provision Doctor account + profile
→ Doctor login
→ create/update Schedule
→ generate 3 slots
→ block 1 slot
→ Patient register
→ discover Specialty/Doctor
→ see 2 AVAILABLE slots
→ book
→ cancel
→ rebook
→ Doctor COMPLETE
→ Doctor create MedicalRecord
→ Patient view read-only History/detail
```

Kết quả: **PASS** bằng Playwright/Edge với UI, API, cookie auth, Backend services và PostgreSQL thật. Không raw UUID, manual SQL, manual API workaround, DEV auth hay seed bypass trong golden path.

## V–X. Post-Phase-14 fixes

| Fix | Kết quả |
| --- | --- |
| ISSUE-001 | **VERIFIED DONE** — candidate link thành công qua UI bằng tên/email và candidate biến mất sau create |
| ENH-001 | **VERIFIED DONE** — provisioning atomic, Doctor login thành công, Argon2/audit/no-orphan regression PASS |
| ISSUE-002 | **VERIFIED DONE** — Doctor tạo/update schedule, sinh/block slot; Patient thấy và book slot |

## Y. Bugs found

| ID | Workflow | Description | Severity | Type | Blocks Golden Path | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| POST14-WF-01 | Admin Doctor Dialog | MUI Select dùng uncontrolled registration, có lúc nhận `undefined`; candidate select render khi data chưa có | MEDIUM | UX ISSUE / INTEGRATION GAP | Có nguy cơ | Browser console warning trong lần Playwright đầu | FIXED |
| POST14-WF-02 | Patient Booking | `InputLabel` của Specialty/Doctor chưa nối `labelId`, combobox không có accessible name | LOW | UX ISSUE | Không với chuột, có với accessibility automation | Playwright accessibility snapshot | FIXED |

Các timeout ban đầu do locator Playwright (`checkbox` thay vì `switch`, portal option scope và strict text match) là lỗi test, không được ghi như lỗi sản phẩm.

## Z. Fixes applied

- Doctor Admin Select chuyển sang React Hook Form `Controller`, giữ value ổn định và candidate/specialty children luôn là mảng.
- Booking Specialty/Doctor Select thêm `labelId` liên kết với `InputLabel`.
- Thêm `e2e/business-workflow.spec.ts` để kiểm chứng candidate link và golden path đa vai trò.
- Không sửa Backend business logic, schema hoặc migration; không sửa module AI.

## AA. Regression results

| Gate | Kết quả thật |
| --- | --- |
| Backend full Pytest + PostgreSQL integration | **162/162 PASS** in 19.11s |
| Frontend Vitest/RTL | **41/41 PASS** (8 files) |
| Frontend ESLint | **PASS**, 0 warning |
| Frontend production build | **PASS**, largest JS 398.03 kB / gzip 124.41 kB |
| Playwright full suite | **4/4 PASS** in 58.5s |
| Golden-path Playwright | **1/1 PASS**; latest full-suite run 44.6s |
| Alembic current/heads/check | **PASS**; `0004_add_json_document_type`; one head; no drift |

## AB. Manual verification required

Không còn manual blocker cho Business Golden Path. Trước buổi demo, cần tự đặt lại password demo Admin/Staff bằng hidden prompt; đây là bước chuẩn bị credential, không phải workflow gap. Các negative/error cases không được kích hoạt từng cái bằng browser vẫn có automated component/API/PostgreSQL integration evidence và được ghi `PASS WITH LIMITATION` ở mục R. Hardware/AI verification nằm ngoài phạm vi task này.

## AC. Final readiness

- **BUSINESS GOLDEN PATH: PASS**
- **ISSUE-001: VERIFIED DONE**
- **ENH-001: VERIFIED DONE**
- **ISSUE-002: VERIFIED DONE**
- **BUSINESS WORKFLOW READINESS: READY**

Không có Phase 15. Không có Chatbot/AI live test trong task này.
