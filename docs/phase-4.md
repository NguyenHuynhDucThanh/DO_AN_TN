# Phase 4 Frontend Core

Ngày hoàn thành: 20/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

## 1. Requirements thực hiện

- Public/Patient: trang chủ, chuyên khoa, bác sĩ, filter theo chuyên khoa, chi tiết, slot khả dụng, booking, hủy lịch, danh sách Appointment, lịch sử khám và chi tiết MedicalRecord chỉ đọc.
- Doctor: lịch làm việc và slot AVAILABLE, Appointment được phân công, COMPLETED/NO_SHOW, tạo và cập nhật MedicalRecord thuộc phạm vi phụ trách.
- Admin: quản lý chuyên khoa, master data bác sĩ và tài liệu RAG metadata/review.
- Staff/Admin: danh sách và state workflow của handoff ticket.
- Dữ liệu client: TanStack Query cho query/mutation và invalidate theo query key.
- Form: React Hook Form + Zod; Backend vẫn quyết định quyền, ownership, business rule và state transition.
- UX: loading, error, empty, success; dịch thông báo 400/401/403/404/409/422; không hiển thị stack trace.
- Responsive: layout Material UI hoạt động ở viewport mobile cơ bản và ưu tiên desktop demo.

## 2. ALREADY IMPLEMENTED được reuse

| Thành phần Phase 3 | Cách reuse ở Phase 4 |
| --- | --- |
| Specialty/Doctor API | Public tra cứu và Admin master data UI |
| Schedule/available slots API | Trang tìm lịch và Doctor schedule UI |
| Appointment API | Booking, cancel, Doctor outcome và danh sách theo actor |
| MedicalRecord API | Doctor create/update; Patient history/detail chỉ đọc |
| Document API | Staff/Admin metadata và Admin APPROVE/REJECT |
| Handoff API | Tạo, xem, tiếp nhận và RESOLVED ticket |
| ActorContext + `X-Dev-User-Id` | DEV actor selector; UUID gửi qua Axios, role thật vẫn lấy từ PostgreSQL |
| Error contract Phase 3 | Hiển thị lỗi có kiểm soát theo HTTP status và `error.detail` |

Không sao chép business logic Backend vào Frontend. Không viết lại service/router/model/table Phase 3.

## 3. PARTIALLY IMPLEMENTED được extend

- Axios client cũ được mở rộng với `VITE_API_BASE_URL`, cookie compatibility và header DEV tập trung.
- AppProviders được mở rộng bằng Theme, QueryClient và DevActorProvider.
- Router một trang được mở rộng thành route tree feature-based có AppShell và role boundary cho UX.
- Home foundation được nâng thành trang chủ nghiệp vụ; health API cũ vẫn không bị thay đổi.
- Material UI theme được mở rộng cho typography, màu sắc, card và responsive layout.

## 4. Thành phần NEW

- Feature folders: `specialties`, `doctors`, `schedules`, `appointments`, `medical-records`, `documents`, `handoffs`, `dev-auth`.
- Shared UI: AppShell, PageHeader, AsyncState, StatusChip, RoleBoundary.
- Domain API clients và TypeScript types.
- Patient, Doctor, Staff/Admin pages và forms.
- Vitest + React Testing Library + jsdom test harness.

## 5. Files tạo và sửa

- Sửa: `package.json`, `package-lock.json`, `.env.example`, `src/api/client.ts`, `src/app/AppProviders.tsx`, `src/pages/HomePage.tsx`, `src/routes/router.tsx`, `src/theme/theme.ts`, `src/vite-env.d.ts`.
- Tạo: `src/api/errors.ts`, `src/types/domain.ts`, `src/utils/format.ts`, shared components/layout, toàn bộ `src/features/*` Phase 4, `src/pages/NotFoundPage.tsx`, `vitest.config.ts`, `src/test/*`.
- Tài liệu: `docs/phase-4.md`, `docs/requirement-traceability.md`, README root và Frontend.
- Không sửa Backend Phase 3.

## 6. Migration

Không có migration. Phase 4 không thay đổi schema. Chuỗi migration giữ nguyên:

`0001_enable_pgvector → 0002_create_business_schema → 0003_phase2_invariants`.

## 7. API và UI mới

Không tạo API Backend mới. Frontend gọi lại 37 operation OpenAPI hiện có.

Route UI chính:

- `/`, `/specialties`, `/specialties/:id`, `/doctors`, `/doctors/:id`, `/booking`.
- `/appointments`, `/medical-history`, `/medical-history/:recordId`.
- `/doctor/schedules`, `/doctor/appointments`, `/doctor/appointments/:appointmentId/medical-record`.
- `/admin/specialties`, `/admin/doctors`, `/admin/documents`, `/handoffs`.

## 8. Tests

Vitest/RTL kiểm tra:

- Specialty list và trạng thái loading/empty/error.
- Doctor filter theo Specialty.
- Available slots.
- Booking form và explicit confirmation.
- Booking conflict 409.
- Cancel Appointment.
- Doctor Appointment outcome.
- MedicalRecord form đủ bốn trường.
- Patient medical history chỉ đọc.
- API failure không lộ stack trace.

Backend regression chạy toàn bộ suite Phase 1-3 với PostgreSQL integration.

## 9. Kết quả test thật

| Lệnh | Kết quả |
| --- | --- |
| `npm test` | 12/12 PASS |
| `npm run lint` | PASS, 0 warning |
| `npm run build` | PASS |
| `$env:RUN_DB_INTEGRATION='1'; python -m pytest -q` | 38/38 PASS |
| Browser + Backend/PostgreSQL thật | Patient Appointment, Patient history, Doctor Appointment và Doctor MedicalRecord load đúng; console không có error/warning |

Vite có cảnh báo bundle chính lớn hơn 500 kB sau minify; đây không phải build failure. Route-level lazy loading có thể bổ sung khi tối ưu performance ở Phase 13 nếu số trang tiếp tục tăng.

## 10. Traceability

- FR-SPE-01..03, FR-DOC-01..03: public pages và Admin management.
- FR-SCH-04: available slot search và Doctor schedule view.
- FR-APT-01, FR-APT-04..08: booking, list, cancel, conflict và Doctor outcome UI.
- FR-MR-01..06, UC-12/13, AC-MR-01..04: Doctor form, Patient history/detail, role-aware routes; Backend ownership/privacy được reuse.
- FR-DOCS-01, FR-DOCS-05..06: metadata/status/review UI; ingestion vẫn Phase 8.
- FR-HO-01..02: ticket UI; WebSocket vẫn Phase 11.
- NFR-USAB-01: loading/error/empty/success.
- BR-06: Frontend chỉ hỗ trợ UX, Backend authoritative.

## 11. Issues và deferred items

- `X-Dev-User-Id` và role selector chỉ dùng development/test. Phase 5 phải giữ ActorContext, thay dependency bằng JWT/Refresh/Argon2/CSRF/RBAC thật.
- Seed hiện có Patient/Doctor/Staff demo; Admin UI cần một UUID User có role ADMIN được cấu hình qua `VITE_DEV_ADMIN_ID`.
- Appointment response hiện chỉ trả `schedule_slot_id`; danh sách hiển thị ID thay vì read model giàu thông tin về ngày/bác sĩ. Không tự tạo dữ liệu ở client. Phase 6 sẽ audit khả năng mở rộng response/read endpoint nếu cần, không viết lại AppointmentService.
- Document UI chỉ quản lý metadata/review. Upload bytes, ingestion, chunking, BGE-M3 và pgvector retrieval thuộc Phase 8 và phải mở rộng Document module hiện có.
- Handoff chỉ REST; WebSocket thuộc Phase 11 và phải mở rộng module hiện có.
- Không có Gemini, RAG, Tool Calling, Voice hoặc auth production trong Phase 4.

## 12. Kết luận

**PHASE 4: PASS.**

Các test bắt buộc đã chạy và đạt. Backend Phase 3 được reuse, không có migration và không tự động triển khai Phase 5.
