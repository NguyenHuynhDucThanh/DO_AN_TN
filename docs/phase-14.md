# Phase 14 — Finalization, Report and Demo

Ngày nghiệm thu: 02/11/2026.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

SRS v1.1 là source of truth. Phase 14 đóng codebase, tổng hợp evidence, chuẩn bị report/demo/defense và chạy final release gates; không thêm feature mới, không thay architecture/business logic và không tạo Phase 15.

## 1. Pre-audit classification

### ALREADY IMPLEMENTED — REUSED

- Business MVP, Auth/RBAC, MedicalRecord, Gemini, RAG V1/V2/V3, Tool Calling, Risk Alert, Handoff/WebSocket và Voice từ Phase 1–13.
- Migration chain `0001_enable_pgvector → 0002_create_business_schema → 0003_phase2_invariants → 0004_add_json_document_type`.
- Phase 13 test/security/performance/bundle evidence and requirement traceability.

### NEEDS SYNC — COMPLETED

- Root README stopped at Phase 11.
- Auth package docstring still described Phase 5 as future.
- Traceability still marked Phase 14 not started.
- Final architecture/report/demo/defense/screenshot materials did not yet exist.
- A newly published npm advisory after Phase 13 affected transitive `follow-redirects`.

### MANUAL CAPTURE REQUIRED

- Real final screenshots for role workflows, AI/provider state, WebSocket and physical microphone. No mock/fake screenshots were created.

## 2. Minimal code/dependency finalization

- Updated only the stale `app/auth/__init__.py` package description; no runtime/business behavior changed.
- Ran non-breaking `npm audit fix`, updating transitive `follow-redirects` to 1.16.2. This removed the newly reported HIGH advisory.
- Did not run `npm audit fix --force`; 12 Moderate findings remain only in ESLint/minimatch development tooling and npm's proposed forced fix would make a breaking toolchain change.
- No architecture refactor, new endpoint, service, table, feature or migration.

## 3. Final source/data/secret audit

- Debug-marker review found operational `print` calls in CLI scripts and temporary-file variable names, not stray application debug breakpoints/console logging.
- `.env` files, build/dependency folders and raw/processed dataset files are ignored. `.gitkeep` preserves RAG folders.
- No file ≥10 MB was found outside excluded dependency/build/git directories. Local controlled dataset files remain ignored.
- Secret pattern review found only synthetic test credentials, placeholders and the development sentinel rejected by production guards; no real key was identified.
- The repository has no committed project history yet (working tree is untracked), so historical secret exposure cannot be audited through Git. Re-scan staged content before first commit.
- Full `vietnamese-medical-dataset.json` is absent and was not ingested.

## 4. Migration/database final state

| Check | Result |
| --- | --- |
| `alembic current` | `0004_add_json_document_type (head)` |
| `alembic heads` | one head: `0004_add_json_document_type` |
| `alembic check` | no new upgrade operations |
| Database checker | PostgreSQL 18.6; pgvector 0.8.7; cosine/vector/Alembic PASS |
| Seed twice | PASS idempotent |

ERD remains aligned with the final schema. No migration was created, edited, squashed or removed in Phase 14.

## 5. Documentation outputs

- Final README for Windows-native setup/run/test/dataset/Voice scope.
- `final-architecture-diagrams.md`: 13 implementation diagrams.
- `final-requirement-matrix.md`: explicit coverage of all 159 SRS v1.1 identifiers.
- `final-test-matrix.md`: final commands, evidence and scope boundary.
- `final-security-findings.md`: final findings/actions/accepted limits.
- `final-rag-dataset-performance.md`: dataset policy, controlled subset, evaluation and measured/not-measured metrics.
- `final-report-materials.md`: business/Auth/AI/RAG/Tool/Risk/Voice/Handoff/Frontend narrative.
- `demo-script.md`: 17-step main demo plus fallback paths.
- `defense-notes.md`: required architecture/technology/safety questions.
- `screenshot-checklist.md`: real manual capture list; no fake screenshot.
- `requirement-traceability.md`: synchronized through Phase 14.

SRS v1.1 and the submitted proposal were not modified.

## 6. Final regression

| Gate | Final result |
| --- | --- |
| Backend full suite + real PostgreSQL integration | **162/162 PASS** (post-checkpoint regression 06/11/2026) |
| Frontend Vitest/RTL | **41/41 PASS** (8 files, post-checkpoint regression) |
| Frontend ESLint | **PASS**, 0 warning |
| Frontend production build | **PASS**, largest JS 398.03 kB / gzip 124.41 kB |
| Playwright Edge scoped release smoke | **3/3 PASS** in 12.9s |
| Python compileall / pip check | **PASS** |
| `pip-audit` | **No known vulnerabilities** |
| npm production audit | **0 vulnerabilities** |
| npm Critical/High gate | **PASS**, none open |
| SRS identifier coverage | **159/159** represented |

Playwright remains scoped; it does not claim full multi-role/Gemini/WebSocket/physical-microphone browser automation.

## 7. Security final state

- Open Critical/High: **0**.
- Runtime/production dependency vulnerabilities reported by current audits: **0**.
- Accepted: 12 Moderate dev-tool-only minimatch findings; per-process limiter for single-instance demo.
- Auth/CSRF/CORS/RBAC/object ownership, MedicalRecord isolation and sanitized error/header/rate-limit protections remain regression-tested.

## 8. RAG and performance final state

- Dataset source is `mtue29/vietnamese-medical-dataset` on Hugging Face.
- Benchmark scope remains **LARGE CONTROLLED SUBSET**: 400 raw, 199 unique/new embedded chunks, 209 actual DB chunks, 50 grounded queries, Top-K=5.
- Runtime strategy: `hnsw_dense`; exact baseline/fallback; V2/V3 experiment only.
- No new benchmark was fabricated. Auth, booking, Gemini, Tool and STT latency are `NOT MEASURED` because no fixed methodology/sample exists.

## 9. Known issues and accepted limitations

1. Vietnamese STT functionality works, but recognition accuracy varies and was poor on the demo hardware; future model/hardware tuning is outside Phase 14.
2. Full approximately 1 GB dataset is absent/not ingested; report uses a controlled subset.
3. Natural “chóng mặt” queries can retrieve mixed/overbroad context because corpus/evaluation coverage is limited.
4. Rate limiting is shared only inside one Backend process; multi-instance deployment needs platform/reverse-proxy shared limiting.
5. Playwright is a 3-case scoped smoke, not full role/provider/realtime/hardware E2E.
6. Long large ingestion is best run through the controlled admin/script workflow, not as an unattended long HTTP request.
7. Gemini is an external dependency; Business MVP remains available when it fails.
8. Twelve Moderate npm advisories remain in development ESLint/minimatch tooling; production audit is clean and there are no Critical/High findings.
9. Final screenshots require manual capture on the real demo session/hardware.

## 10. Final release readiness

**PHASE 14: PASS.**

**FINAL RELEASE READINESS: READY cho phạm vi đồ án tốt nghiệp/demo có kiểm soát.**

The project is not claimed as certified production healthcare software or a diagnosis system. After this checkpoint, do not add features; only mandatory bug fixes are allowed and must be followed by relevant regression.

## 11. Post-checkpoint workflow fixes hoàn thành ngày 06/11/2026

- **ISSUE-001 DONE:** Admin không còn nhập raw `User UUID`; có thể chọn tài khoản Doctor hợp lệ từ dropdown.
- **ENH-001 DONE:** cùng Dialog cho phép Admin tạo đồng thời User role `DOCTOR` và Doctor profile trong một transaction; mật khẩu khởi tạo được băm Argon2 và không xuất hiện trong audit.
- **ISSUE-002 DONE:** Doctor Schedule UI hỗ trợ tạo/sửa/hủy lịch, sinh slot và block/unblock; Patient có thể thấy slot `AVAILABLE` được tạo từ workflow thật.
- Backend reuse Doctor/Schedule services, ownership, advisory overlap lock và validation hiện có. Chỉ bổ sung endpoint/read method và orchestration cần thiết; không tạo service/model/table trùng.
- Không thay đổi schema và không tạo migration mới.

Post-checkpoint evidence: Backend **162/162 PASS**; Frontend **41/41 PASS**; lint 0 warning; production build PASS. Chi tiết nằm trong `known-issues-tracker.md` và `doctor-user-selection-fix-plan.md`.
