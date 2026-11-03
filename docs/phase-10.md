# Phase 10 — AI MVP và Risk Alert

Ngày nghiệm thu: 26/10/2026. SRS v1.1 là source of truth; SRS, roadmap và schema database không bị thay đổi. Phase 10 hoàn thiện pipeline AI duy nhất bằng cách mở rộng `ChatOrchestrator` Phase 9, không tạo chatbot hoặc business service thứ hai.

## Phân loại trước implementation

| Nhóm | Kết quả audit |
| --- | --- |
| ALREADY IMPLEMENTED / REUSED | GeminiClient, RAG V1, ToolExecutor, explicit booking confirmation, HandoffService, ActorContext/JWT, Chat UI và các business services Phase 3–9. |
| PARTIALLY IMPLEMENTED / EXTENDED | ChatOrchestrator đã có nhưng luôn retrieval trước Gemini; fallback nằm rải theo RAG/Gemini/Tool; UI chưa có Risk Alert. |
| NOT IMPLEMENTED / NEW | Deterministic intent routing; rule-based Risk Alert; fixed scenarios/false-positive guards; risk-first orchestration; urgent handoff adapter; Risk Alert response/UI/tests. |

## Pipeline thống nhất

```text
Input
→ deterministic Risk Alert check
   ├─ trigger → fixed safety warning → existing HandoffService → response
   └─ no trigger
      → deterministic top-level route
         ├─ KNOWLEDGE → RAG V1 → Gemini grounded answer + sources
         ├─ BUSINESS/BOOKING/HANDOFF → Gemini function call
         │  → ToolExecutor → existing Business Service → PostgreSQL
         └─ controlled fallback
```

Risk được kiểm tra trước retrieval và Gemini nên cảnh báo không thể bị mô hình che mất. Router FastAPI chỉ nhận request/ActorContext và gọi ChatService; orchestration nằm trong `ChatOrchestrator`.

## Routing

- `KNOWLEDGE`: gọi lại `RagService.answer`; nguồn chỉ từ Document đã APPROVED/COMPLETED.
- `BUSINESS_LOOKUP`: Doctor/Specialty/Schedule/Slot đi qua tool và business service thật; không retrieval corpus.
- `BOOKING`: giữ nguyên `CONFIRMATION_REQUIRED`, token actor-bound và nút xác nhận Phase 9.
- `HANDOFF`: Gemini chọn `handoff_to_staff`, sau đó ToolExecutor gọi HandoffService; final response không phụ thuộc lần gọi Gemini thứ hai.
- Risk Alert: short-circuit toàn bộ RAG/Gemini/booking flow.

## Risk Alert rule-based

`RiskAlertService` là pure rule engine, không gọi Gemini, database hoặc MedicalRecord. Tập demo có mã cố định:

- `RISK-RESPIRATORY`: không thở được/ngừng thở/khó thở dữ dội.
- `RISK-CHEST`: đau ngực dữ dội hoặc đau ngực kèm khó thở/vã mồ hôi.
- `RISK-STROKE`: liệt/yếu nửa người hoặc nói ngọng đột ngột.
- `RISK-BLEEDING`: chảy máu không cầm/không ngừng hoặc mất máu nhiều.
- `RISK-CONSCIOUSNESS`: bất tỉnh/hôn mê/co giật kéo dài.
- `RISK-POISONING`: ngộ độc/quá liều.
- `RISK-SELF-HARM`: diễn đạt ý định tự gây hại trực tiếp.

Engine normalize Unicode/tiếng Việt, kiểm tra negation và loại các câu hỏi giáo dục như “dấu hiệu ... là gì” hoặc “tìm hiểu về ...”. Đây là safety net demo, không phải công cụ chẩn đoán; false positive/false negative vẫn có thể xảy ra và Phase 13 phải đánh giá sâu hơn.

Khi trigger, Backend trả cảnh báo cố định nêu rõ “không phải chẩn đoán”, khuyến nghị tìm trợ giúp y tế/cấp cứu phù hợp và không kê đơn. Gemini không được gọi.

## Handoff

Risk path mở rộng chính `HandoffService` bằng `create_risk_alert`, không tạo Handoff service thứ hai. Ticket dùng:

- source `RISK_ALERT`;
- priority `URGENT`;
- status `PENDING`;
- requester lấy từ ActorContext;
- reason chỉ chứa mã rule, không lưu nguyên văn nội dung sức khỏe.

Nếu tạo ticket lỗi, cảnh báo vẫn hiển thị với trạng thái handoff `FAILED` và hướng dẫn dùng liên hệ thủ công. PostgreSQL handoff vẫn là nguồn sự thật; WebSocket notification thuộc Phase 11.

## Fallback và privacy

- Empty retrieval dùng fixed no-context answer và không gọi Gemini.
- Gemini/RAG/Tool failure dùng ApplicationError an toàn; không trả raw provider/database error.
- Risk warning không bị mất nếu handoff lỗi.
- Business MVP và các API thủ công không phụ thuộc AI.
- Không có MedicalRecord tool/import/query/corpus/context; không dùng hồ sơ bệnh nhân để đánh giá risk.

## Frontend

Chat UI hiện hỗ trợ text, RAG sources, tool results, booking confirmation/result/conflict, Risk Alert và handoff `PENDING`/`FAILED`. Cảnh báo dùng vùng error riêng, hiển thị hành động khuyến nghị và không tạo booking card. Voice chưa được triển khai.

## Database và migration

Không có schema change. Alembic vẫn ở `0004_add_json_document_type`; `alembic check` không phát hiện operation mới.

## Test và kiểm chứng

- Backend full regression với PostgreSQL thật: **136/136 PASS**.
- Frontend Vitest/RTL: **29/29 PASS**.
- Frontend ESLint: PASS, 0 warning.
- Frontend production build: PASS; cảnh báo bundle >500 kB không chặn build.
- Positive fixed scenarios: 7 nhóm rule PASS.
- Negative/negation/educational false-positive cases PASS.
- Risk-before-RAG/Gemini, handoff failure fallback, knowledge→RAG, Doctor/slot→Tool, booking confirmation, 409, empty retrieval, Gemini/RAG/Tool failure và MedicalRecord isolation PASS.
- PostgreSQL thật xác nhận risk handoff `URGENT`, `PENDING`, source `RISK_ALERT`, không lưu raw symptom text.
- OpenAPI version `0.10.0`; ChatResponse có `risk_alert`.

## Files chính

- New: `app/ai/risk/rules.py`, `app/ai/risk/service.py`, `app/ai/routing.py`, `tests/test_phase10_ai_mvp.py`, `src/test/phase10.test.tsx`.
- Extended: `app/ai/orchestrator.py`, `app/ai/schemas.py`, `app/ai/tools/executor.py`, `app/handoffs/service.py`, `src/features/chat/api.ts`, `src/features/chat/ChatPage.tsx`.
- Không có migration.

## Deferred đúng roadmap

- Voice + Handoff WebSocket thuộc Phase 11.
- RAG V2/V3 thuộc Phase 12.
- Mở rộng evaluation, adversarial safety, rate limiting và security review thuộc Phase 13.

**PHASE 10: PASS.**

