# Phase 5 Authentication and RBAC

Ngày hoàn thành: 21/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

## 1. Requirements thực hiện

- FR-AUTH-01: Patient đăng ký bằng email duy nhất, password, full_name và phone bắt buộc; date_of_birth/gender tùy chọn.
- FR-AUTH-02/UC-01: đăng nhập email/password, email case-insensitive và chỉ chấp nhận User ACTIVE.
- FR-AUTH-03: đăng xuất, revoke refresh session và xóa cookie.
- FR-AUTH-04: refresh token rotation, chỉ lưu token hash, phát hiện reuse và revoke toàn bộ session family.
- FR-AUTH-05/06: xem current user và cập nhật profile; Patient không được xóa phone.
- NFR-SEC-01..04: Argon2, JWT access ngắn hạn, HttpOnly cookie, CSRF double-submit, exact Origin/CORS, không đưa token/password vào log hoặc localStorage.
- RBAC và object-level authorization: role luôn lấy từ PostgreSQL; MedicalRecord giữ nguyên Patient own-read, Doctor ownership và chặn Staff/Admin đọc clinical content mặc định.

## 2. ALREADY IMPLEMENTED được reuse

| Thành phần Phase trước | Cách reuse ở Phase 5 |
| --- | --- |
| `ActorContext` | Giữ nguyên interface `user_id` và `roles`; JWT/session dependency tạo ActorContext cho business services hiện có. |
| User, Role, UserRole | Dùng trực tiếp để kiểm tra User ACTIVE và role active từ PostgreSQL. |
| RefreshSession | Tái sử dụng `token_hash`, `family_id`, `replaced_by_session_id`, `revoked_at`, `expires_at`, `last_used_at`. |
| Case-insensitive email index | Login/register normalize email và dựa trên `uq_users_email_ci`. |
| Business services Phase 3 | Không viết lại ScheduleService, AppointmentService, MedicalRecordService, DocumentService hoặc HandoffService. |
| Exact CORS + Axios | Giữ exact frontend origin và `withCredentials`; mở rộng thêm CSRF/refresh handling. |
| MedicalRecord authorization | Ownership và clinical privacy vẫn nằm trong MedicalRecordService, Backend authoritative. |

## 3. PARTIALLY IMPLEMENTED được extend

- `get_current_actor` được mở rộng từ DEV identity thành JWT cookie → User/roles DB → ActorContext.
- `UserRepository` được bổ sung case-insensitive lookup, active role lookup, add và role assignment.
- Frontend role boundary được thay bằng ProtectedRoute/RoleRoute dùng session thật.
- Axios client được bổ sung CSRF header, refresh một lần khi 401 và session-expired event.
- Seed synthetic được bổ sung Admin demo; password seed vẫn là sentinel không đăng nhập được.

## 4. Thành phần NEW

- Backend: password hashing, JWT/opaque refresh token helpers, CSRF/Origin validation, cookie policy, refresh-session repository, AuthService và auth router.
- API đăng ký, đăng nhập, refresh, logout, current user và cập nhật profile.
- Frontend: AuthProvider, LoginPage, RegisterPage, ProtectedRoute, RoleRoute và session restore/logout UX.
- Script `set_demo_password.py` nhập password ẩn, chỉ cho tài khoản `@example.invalid`, lưu Argon2 hash và bị chặn trong production.
- Test Backend/Frontend Phase 5.

## 5. Files tạo và sửa

Backend tạo mới:

- `app/auth/passwords.py`, `tokens.py`, `csrf.py`, `cookies.py`, `repository.py`, `schemas.py`, `service.py`, `router.py`.
- `app/users/schemas.py`, `service.py`, `router.py`.
- `scripts/set_demo_password.py`.
- `tests/test_phase5_auth_integration.py`.

Backend sửa:

- `app/auth/dependencies.py`, `app/users/repository.py`, `app/core/config.py`, `app/core/errors.py`.
- `app/api/v1/router.py`, `app/main.py`, `requirements.txt`, `requirements.lock.txt`, `.env.example`, `scripts/seed_demo.py`.
- `tests/test_health.py`, README.

Frontend tạo mới:

- `features/auth/api.ts`, `types.ts`, `AuthContext.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`.
- `components/ProtectedRoute.tsx`, `components/RoleRoute.tsx`.
- `test/phase5.test.tsx`.

Frontend sửa:

- `api/client.ts`, `api/errors.ts`, `app/AppProviders.tsx`, `routes/router.tsx`, `layouts/AppShell.tsx`.
- Các màn hình Doctor schedules, Documents và Handoffs chuyển từ DEV actor sang authenticated user.
- DEV actor switcher chỉ xuất hiện khi bật cờ development; `.env.example` và README được cập nhật.

Tài liệu sửa/tạo: README root, README Backend/Frontend, `docs/phase-5.md`, `docs/requirement-traceability.md`.

## 6. Migration

Không có migration mới. Schema Phase 2 đã đủ trường cho Phase 5. Chuỗi migration giữ nguyên:

`0001_enable_pgvector → 0002_create_business_schema → 0003_phase2_invariants`.

## 7. API và UI mới

API:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `PATCH /api/v1/users/me`

UI:

- `/register`
- `/login`
- Session restore khi tải lại ứng dụng.
- ProtectedRoute cho màn hình cần đăng nhập.
- RoleRoute cho Patient/Doctor/Staff/Admin.
- Nút logout và điều hướng theo role thật.

## 8. Tests

Backend kiểm tra:

- Register, duplicate email và Patient thiếu phone.
- Argon2 hash, không lưu plaintext.
- Invalid password, case-insensitive login và inactive user.
- Access JWT, token hết hạn và không fallback âm thầm sang DEV header.
- Refresh rotation, token hash, replaced session, reuse detection và family revocation.
- Logout, revoked session và cookie clearing.
- CSRF header, exact Origin và CORS.
- 401/403, role-level authorization và MedicalRecord object-level privacy bằng auth thật.
- DEV auth bị vô hiệu trong production.
- Current user/profile update và Patient phone invariant.

Frontend kiểm tra:

- Login và register flow.
- Logout.
- ProtectedRoute và RoleRoute.
- Expired-session event.
- Safe 401 feedback; không hiển thị stack trace.
- Regression toàn bộ 12 test Frontend Core Phase 4.

## 9. Kết quả test thật

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| Backend Pytest với PostgreSQL integration | 46/46 PASS |
| Frontend Vitest + React Testing Library | 19/19 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS |
| Alembic current/check | `0003_phase2_invariants (head)`; không có operation mới |
| Browser + Backend/PostgreSQL thật | Login bằng cookie thật, mở route Patient được bảo vệ, logout và redirect về login đúng; console không có error/warning |

## 10. Traceability

- FR-AUTH-01, DR-04: Register Patient, phone bắt buộc, Argon2 password hash.
- FR-AUTH-02, UC-01: case-insensitive login và ACTIVE-user check.
- FR-AUTH-03: logout/revocation/cookie clearing.
- FR-AUTH-04: refresh rotation và reuse handling.
- FR-AUTH-05/06: `/auth/me` và `/users/me`.
- NFR-SEC-01..04: Argon2, Backend token validation, HttpOnly cookie, CSRF/Origin/CORS và secret separation.
- RBAC/BR-06: role DB + ActorContext; Backend authoritative.
- BR-22, NFR-PRIV-02, NFR-TEST-02, AC-MR-01..03: MedicalRecord ownership/privacy được reuse và kiểm tra qua auth thật.
- AC-BIZ-01: register/login/logout và RBAC hoạt động ở các luồng Phase 5.

## 11. Issues và deferred items

- Local development có fallback JWT secret để không phá setup cũ; production startup từ chối fallback này và yêu cầu JWT secret riêng, HTTPS origin, Secure cookie, `DEV_AUTH_ENABLED=false`.
- Tài khoản demo seed dùng password sentinel. Muốn demo login Doctor/Staff/Admin phải chạy script nhập password ẩn; không hard-code credential.
- Rate limiting/brute-force protection tổng thể và security evaluation mở rộng thuộc Phase 13; không thêm Redis chỉ cho Phase 5.
- Password reset, email verification và MFA không có trong SRS v1.1 nên không tự mở rộng phạm vi.
- Không triển khai hoặc thay đổi Gemini, RAG, Tool Calling, WebSocket hay Voice.

## 12. Kết luận

**PHASE 5: PASS.**

JWT/Refresh/Argon2/HttpOnly Cookie/CSRF/RBAC thật hoạt động; ActorContext và business services Phase 3 được reuse. Không có migration mới và không tự động triển khai Phase 6.
