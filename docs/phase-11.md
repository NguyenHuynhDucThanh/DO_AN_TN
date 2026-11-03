# Phase 11 Voice and Handoff WebSocket

Ngày hoàn thành: 28/10/2026, múi giờ Asia/Saigon.

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn**.

## 1. Kết quả audit

| Phân loại | Thành phần |
| --- | --- |
| ALREADY IMPLEMENTED / REUSED | ChatOrchestrator, RiskAlertService, RagService, ToolExecutor, booking confirmation, ActorContext/JWT cookie, HandoffRequest, HandoffService, Handoff REST API và Handoff UI. |
| PARTIALLY IMPLEMENTED / EXTENDED | Handoff transaction và REST reload được mở rộng bằng notification/status WebSocket; Chat UI text được mở rộng bằng push-to-talk và TTS. |
| NOT IMPLEMENTED / NEW | Realtime connection manager, authenticated WebSocket route, reconnect hook, faster-whisper transcription endpoint, MediaRecorder controls và browser SpeechSynthesis controls. |

Không tạo Handoff model/service/workflow thứ hai và không tạo Voice chatbot riêng. PostgreSQL tiếp tục là nguồn sự thật.

## 2. Handoff WebSocket

Endpoint mới: `WS /api/v1/handoffs/ws`.

- Xác thực bằng HttpOnly access cookie hiện có; signature, expiry, User ACTIVE và role được kiểm tra lại từ Backend/PostgreSQL.
- Origin phải trùng chính xác `FRONTEND_ORIGIN`; không nhận `user_id` hoặc role từ client.
- Chỉ Staff/Admin được subscribe. Patient vẫn xem ticket của mình qua REST theo quyền hiện có.
- Sự kiện `handoff.created` và `handoff.updated` chỉ được phát sau khi HandoffService commit thành công.
- Ticket do User, Tool Calling hoặc Risk Alert tạo đều đi qua HandoffService hiện có rồi dùng cùng notification layer.
- Payload WebSocket chỉ có metadata định danh/trạng thái/priority/source/timestamp; không phát `reason`, raw prompt hoặc nội dung MedicalRecord.
- Nếu publish hoặc kết nối WebSocket lỗi, transaction PostgreSQL và Handoff REST không bị rollback. Sau reconnect, Frontend invalidate và tải lại danh sách authoritative từ REST.
- Realtime manager chạy trong process Uvicorn hiện tại, phù hợp demo Windows một Backend process. Không thêm Redis; mở rộng multi-instance pub/sub là future deployment concern, không phải SRS MVP.

Không triển khai Patient-Staff live chat.

## 3. Voice push-to-talk

Frontend dùng microphone có sẵn của thiết bị qua:

- `navigator.mediaDevices.getUserMedia({ audio: true })`;
- `MediaRecorder` để start/stop và tạo audio Blob;
- dừng toàn bộ MediaStream track sau khi ghi xong hoặc khi component unmount;
- fallback text rõ ràng khi unsupported, không có microphone hoặc bị từ chối permission.

Endpoint mới: `POST /api/v1/voice/transcriptions`, multipart field `audio`.

Backend kiểm tra empty file, MIME cho phép và giới hạn kích thước; không tin filename client. Bytes được ghi vào file tạm có suffix do Backend chọn, chuyển cho faster-whisper với `language="vi"`, rồi xóa trong `finally` cả khi thành công hoặc lỗi. Audio không được lưu vào database, không gửi Gemini và không được ghi log. Model mặc định `small`, CPU `int8`, cấu hình qua `.env`; model được tải lazy ở lần dùng đầu tiên. BGE-M3 và faster-whisper dùng khóa runtime chung: BGE-M3 được giải phóng trước STT, Whisper được giải phóng sau STT, tránh giữ đồng thời hai model nặng trên máy Windows demo. Dependency khóa `av==18.1.0` vì `faster-whisper==1.2.1` chưa tương thích API giải mã đã thay đổi của PyAV 19.

Transcript được đưa trở lại đúng form text hiện có. User xem/sửa transcript rồi bấm Gửi; request tiếp tục qua ChatOrchestrator Phase 10, nên Gemini/RAG/Tool/Risk Alert/Handoff và booking confirmation đều được reuse.

## 4. TTS

Frontend dùng `window.speechSynthesis` và `SpeechSynthesisUtterance`. UI ưu tiên voice có locale `vi-*`, fallback `vi-VN`/voice mặc định, có nút đọc và dừng. Text response luôn hiển thị và không phụ thuộc TTS.

Không có wake word, always-listening, full-duplex, voice cloning, server-side TTS hoặc SSE trong Phase 11.

## 5. Security và privacy

- Voice upload dùng auth/CSRF/Origin hiện có.
- WebSocket dùng cookie/JWT và exact Origin; không fallback sang identity do client khai báo.
- Không lưu audio hoặc microphone stream lâu dài.
- Không log raw audio, transcript, token hoặc secret.
- MedicalRecord không được đưa vào Voice, WebSocket, Gemini, RAG, Tool Calling hoặc Risk Alert.
- WebSocket không phát nội dung clinical và không giữ state nghiệp vụ.

## 6. Files tạo và sửa

Backend tạo mới:

- `app/voice/__init__.py`, `schemas.py`, `service.py`, `router.py`.
- `app/handoffs/realtime.py`.
- `tests/test_phase11_voice_websocket.py`.

Backend mở rộng:

- `app/auth/dependencies.py`, `app/handoffs/router.py`, `app/ai/tools/executor.py`.
- `app/api/v1/router.py`, `app/core/config.py`, `app/main.py`.
- `requirements.txt`, `requirements.lock.txt`, `.env.example`.

Frontend tạo mới:

- `features/chat/VoiceControls.tsx`.
- `features/handoffs/useHandoffRealtime.ts`.
- `test/phase11.test.tsx`.

Frontend mở rộng:

- `api/client.ts`, `features/chat/api.ts`, `features/chat/ChatPage.tsx`.
- `features/handoffs/api.ts`, `features/handoffs/HandoffPage.tsx`.
- Test boundary Phase 7 được bỏ assertion lịch sử “không có ghi âm” vì Phase 11 đã bổ sung Voice; hành vi Phase 7 còn lại vẫn được regression.

## 7. Database và migration

Không thay đổi schema, không tạo table Handoff mới và không có migration Phase 11. Alembic giữ head `0004_add_json_document_type`; `alembic check` báo không có operation mới.

## 8. Tests và kiểm chứng

Backend Phase 11 kiểm tra:

- audio success/Vietnamese transcript;
- empty, unsupported, oversized, corrupt/no-speech và cleanup file tạm;
- faster-whisper được gọi với language `vi`;
- WebSocket authenticated/unauthorized/wrong-role;
- event metadata không chứa reason/MedicalRecord;
- socket failure không làm hỏng publisher còn hoạt động.

Frontend Phase 11 kiểm tra:

- getUserMedia success, permission denied và unsupported fallback;
- MediaRecorder start/stop, Blob upload, stream-track cleanup;
- transcript đi vào form và request chat hiện có;
- SpeechSynthesis play/stop;
- WebSocket connect/event/disconnect/reconnect và REST query invalidation.

Kết quả thật:

| Kiểm tra | Kết quả |
| --- | --- |
| Backend Phase 11 targeted | 8/8 PASS |
| Backend full regression với PostgreSQL thật | 144/144 PASS |
| Frontend Phase 11 targeted | 8/8 PASS |
| Frontend full regression | 37/37 PASS |
| Frontend ESLint | PASS, 0 warning |
| Frontend production build | PASS; chỉ còn cảnh báo bundle khoảng 878 kB |
| `pip check` | PASS |
| Alembic current/check | `0004_add_json_document_type (head)`; không có operation mới |
| OpenAPI | Version `0.11.0`; transcription endpoint có trong schema |

Automated test không dùng microphone hardware; Browser APIs được mock. Manual live test ngày 28/10/2026 đã xác nhận browser nhận microphone vật lý, permission và MediaRecorder hoạt động, audio được upload tới endpoint thật, faster-whisper decode/inference thành công, file tạm được cleanup và transcript xuất hiện trong Chat UI để User xem/sửa trước khi gửi. Tuy nhiên, độ chính xác tiếng Việt của cấu hình local hiện tại chưa đạt mức chấp nhận cho demo ổn định: câu ngắn có thể bị nhận sai đáng kể, ví dụ câu nói “tôi bị đau tim” từng được nhận thành “Toi video team”. Vì vậy, pipeline live được xác nhận hoạt động nhưng **Live Vietnamese STT quality acceptance chưa PASS**.

## 9. Issues và deferred

- Lần đầu STT sẽ tải model faster-whisper cấu hình; thời gian phụ thuộc mạng và cache máy.
- Máy demo có RTX 3050 Ti Laptop GPU với khoảng 4 GB VRAM. GPU và CTranslate2 đã được kiểm tra bằng inference thật với `small + cuda + float16`, nhưng giới hạn VRAM làm giảm dư địa sử dụng ổn định các model Whisper lớn hơn. Cấu hình chính thức hiện vẫn giữ `small + cpu + int8` và CPU fallback để ưu tiên khả năng chạy được trên Windows.
- Vietnamese STT local hiện được đánh dấu **LIMITED / DEFERRED QUALITY TUNING**. Phase 11 không tuyên bố độ chính xác đã cải thiện khi chưa có benchmark cố định và bằng chứng WER/CER.
- Hướng phát triển tương lai: xây dựng tập audio tiếng Việt cố định; benchmark `small` và `medium`; thử `medium + cuda + float16` hoặc `int8_float16` theo giới hạn VRAM; đo WER/CER, latency và độ ổn định; đánh giá hotwords y tế nhỏ hoặc Cloud STT nếu phù hợp chi phí và privacy.
- Transcript không được tự động gửi. User luôn phải xem/sửa rồi chủ động bấm Gửi; đây là safety boundary bắt buộc khi STT còn khả năng nhận sai.
- WebSocket layer là best-effort single-process cho MVP; PostgreSQL/REST xử lý mọi trường hợp mất event.
- SSE Gemini streaming không triển khai vì optional và không cần để Phase 11 đạt yêu cầu.
- RAG V2/V3 vẫn thuộc Phase 12.

## 10. Kết luận

**PHASE 11 IMPLEMENTATION VÀ AUTOMATED REGRESSION: PASS.**

**LIVE VOICE PIPELINE: PASS; LIVE VIETNAMESE STT QUALITY: LIMITED / NOT PASS, DEFERRED TO FUTURE WORK.**

Voice là input/output layer của chatbot hiện có; Handoff WebSocket là notification/status layer của workflow hiện có. Business MVP, text chat, Handoff REST và MedicalRecord privacy vẫn hoạt động độc lập khi Voice/WebSocket không khả dụng. Giới hạn chất lượng STT đã được ghi nhận minh bạch và không được dùng để tuyên bố live quality PASS. Phase 12 có thể được thực hiện độc lập theo roadmap, nhưng không được hiểu là đã hoàn tất phần tuning chất lượng STT nêu trên.
