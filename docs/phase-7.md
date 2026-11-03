# Phase 7 Gemini Basic Chatbot

Ngày audit và triển khai: 22/10/2026; nghiệm thu real API: 23/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

Phase 7 tích hợp chatbot TEXT cơ bản qua Gemini API. Phase này không có RAG, Tool Calling, Voice, AI booking hoặc Risk Alert đầy đủ. Business MVP Phase 6 không phụ thuộc Gemini.

## 1. Audit trước implementation

### ALREADY IMPLEMENTED

- Modular Monolith, API error contract, Pydantic validation và OpenAPI.
- JWT/refresh cookie, CSRF, exact Origin/CORS và `ActorContext`.
- Axios/TanStack Query, protected routes và loading/error UX.
- Business MVP hoạt động độc lập AI.

### PARTIALLY IMPLEMENTED

- Cơ chế backend settings và `.env` có thể mở rộng cho Gemini.
- Frontend feature structure, API client và navigation có thể reuse cho chat.

### NOT IMPLEMENTED

- Google Gen AI SDK, Gemini client, ChatService/router/schema.
- Safety instruction, provider failure mapping và smoke verification.
- Chatbot text UI và automated tests.

## 2. SDK và model

- SDK hiện hành được chọn là `google-genai==2.32.0`, không dùng SDK legacy. Google hướng dẫn import `from google import genai` và cung cấp async API qua `client.aio.models.generate_content`: [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/).
- Model không hard-code trong source. Backend đọc `GEMINI_MODEL`; `.env.example` chỉ đề xuất `gemini-3.5-flash-lite` theo catalog model hiện hành: [Gemini models](https://ai.google.dev/gemini-api/docs/models).
- API key chỉ nằm ở Backend trong `GEMINI_API_KEY`, được che bởi `SecretStr`, không xuất hiện trong Vite hoặc source control. Google cũng yêu cầu không đưa key vào client-side: [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key).

## 3. REUSED

| Thành phần | Cách reuse |
| --- | --- |
| `ActorContext` và auth dependency | Chat endpoint yêu cầu phiên hợp lệ; không đưa actor/profile vào prompt. |
| Application error handler | Chuyển lỗi chatbot thành payload `error.code/detail` an toàn. |
| Axios/CSRF/session refresh | Frontend chat dùng cùng API client, HttpOnly cookie và CSRF. |
| ProtectedRoute/AppShell | Chatbot dùng được bởi PATIENT/DOCTOR/STAFF/ADMIN đã đăng nhập. |
| Business MVP | Specialty, Doctor, Schedule, Appointment, MedicalRecord, Document và Handoff không import/phụ thuộc Gemini. |

## 4. NEW

- Backend `app/ai/`: schemas, safe errors, async Gemini adapter, ChatService và router.
- `POST /api/v1/chat/messages` với request `{message, history}` và response ổn định `{answer}`.
- Safety instruction giới hạn chẩn đoán, kê đơn, quyết định điều trị, suy đoán và giả làm bác sĩ.
- Failure mapping cho timeout, network, 429, 400, 401/403, model 404, provider 5xx và response rỗng/không hợp lệ.
- Frontend `/chat`: message list, input, loading, safe error, retry và unavailable state.
- `scripts/check_gemini.py` để kiểm tra model và generation thật tách khỏi regression.

## 5. Files tạo/sửa

Tạo:

- `healthcare-backend/app/ai/__init__.py`
- `healthcare-backend/app/ai/errors.py`
- `healthcare-backend/app/ai/schemas.py`
- `healthcare-backend/app/ai/gemini_client.py`
- `healthcare-backend/app/ai/chat_service.py`
- `healthcare-backend/app/ai/router.py`
- `healthcare-backend/scripts/check_gemini.py`
- `healthcare-backend/tests/test_phase7_chat.py`
- `healthcare-frontend/src/features/chat/api.ts`
- `healthcare-frontend/src/features/chat/ChatPage.tsx`
- `healthcare-frontend/src/test/phase7.test.tsx`
- `docs/phase-7.md`

Sửa:

- Backend config, API router, dependency/lock files, `.env.example`, config tests và app version.
- Frontend router, navigation và nhãn phase trang chủ.
- README và requirement traceability.

Không sửa SRS, business services, database model hoặc migration.

## 6. Config và environment

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=20
```

- Key/model thiếu không làm Backend khởi động thất bại; chỉ chat endpoint trả `503 chatbot_not_configured`.
- `GEMINI_API_KEY` không có trong Frontend, OpenAPI response hoặc log.
- Model chỉ được coi là sẵn sàng sau khi `scripts/check_gemini.py` PASS bằng key thật.

## 7. API và UI

Flow hiện tại:

```text
React ChatPage
→ Axios cookie/CSRF
→ FastAPI chat router
→ ChatService
→ GeminiClient async
→ Gemini API
```

ChatService không nhận `Session`, `ActorContext`, patient profile hoặc business service. History tối đa 10 message được giữ trong React state và gửi kèm request; không có `ChatSession`/`ChatMessage` table và không coi history là MedicalRecord.

## 8. Safety và privacy

- Không chẩn đoán chắc chắn, kê đơn, quyết định điều trị hoặc giả làm bác sĩ.
- Nói rõ giới hạn và khuyến nghị gặp nhân viên y tế khi cần.
- Không có RAG, citations, tools, function declarations, Voice hoặc AI booking.
- `automatic_function_calling` bị disable và request không có tools.
- Module AI không import MedicalRecord, Appointment, Schedule, Document, Handoff, SQLAlchemy hay pgvector.
- Prompt/response không được log.

## 9. Tests và regression result

| Hạng mục | Kết quả |
| --- | --- |
| Backend Phase 7 mock tests | 21/21 PASS |
| Backend full suite với PostgreSQL integration | 75/75 PASS |
| Frontend Phase 7 UI tests | 4/4 PASS |
| Frontend full Vitest/RTL | 23/23 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; cảnh báo chunk lớn không chặn build |
| Python dependency check | PASS |
| Alembic | Head `0003_phase2_invariants`; autogenerate check sạch |

Test bao phủ success, empty/too-long/malformed input, timeout, network, 429, authentication, model unavailable, provider 5xx, invalid/empty/function-call response, safety instruction, stable contract, MedicalRecord/RAG/tool isolation và Business health khi Gemini lỗi.

## 10. Gemini real API smoke result

Lệnh:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_gemini.py
```

Kết quả nghiệm thu lại ngày 23/10/2026 sau khi cấu hình `.env` local:

```text
GEMINI_API_KEY_SET=True
GEMINI_MODEL_SET=True
PASS: configured Gemini model is available and returned text.
```

Smoke script đã nạp key/model từ Backend mà không in giá trị bí mật, gọi đúng model cấu hình qua Gemini API thật và nhận được text. API key vẫn chỉ nằm trong `.env` local bị Git ignore.

## 11. Issues và deferred items

- Không còn blocker nghiệm thu Phase 7. Khi key hết hiệu lực, hết quota hoặc provider gián đoạn, chatbot trả lỗi có kiểm soát và Business MVP vẫn hoạt động.
- RAG/pgvector retrieval thuộc Phase 8.
- Tool Calling và AI booking thuộc Phase 9.
- Risk Alert đầy đủ thuộc Phase 10.
- Voice và Handoff WebSocket thuộc Phase 11.
- Chat persistence không có requirement bắt buộc trong Phase 7 nên không tạo schema.

## 12. Kết luận

**PHASE 7: PASS.**

Implementation, real Gemini model/generation smoke, mock tests, failure isolation, safety baseline, MedicalRecord isolation và regression Phase 1-6 đều PASS. Business MVP vẫn chạy khi Gemini chưa cấu hình hoặc provider lỗi. Phase 8 chưa được bắt đầu.
