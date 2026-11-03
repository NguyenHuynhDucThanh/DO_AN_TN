# Healthcare Frontend

Project React + TypeScript + Vite độc lập. Phase 4-6 hoàn thiện Business UI; Phase 8-10 hoàn thiện RAG/Tool/Risk UI; Phase 11 thêm push-to-talk bằng microphone thật của thiết bị, Browser TTS và Handoff WebSocket reconnect; Phase 13 bổ sung route-level code splitting và Playwright release smoke; Phase 14 chốt dependency/report/demo mà không thêm feature.

## Chạy trên PowerShell

```powershell
npm.cmd ci
Copy-Item .env.example .env   # Chỉ lần đầu, khi chưa có .env
npm.cmd run dev
```

Mở <http://localhost:5173>. Backend phải cho phép chính xác origin này. `VITE_API_BASE_URL` mặc định là `http://localhost:8000/api/v1`; giữ cùng hostname `localhost` để SameSite cookie hoạt động đúng. Khởi động lại Vite sau khi thay `.env`.

Mặc định `VITE_ENABLE_DEV_AUTH=false`, Frontend dùng session cookie thật. Axios tự gửi credentials và CSRF header, thử refresh đúng một lần khi access token hết hạn, sau đó đưa ứng dụng về trạng thái anonymous nếu session không thể khôi phục. Password/access token/refresh token không được lưu trong localStorage.

Nếu cần kiểm thử nội bộ dữ liệu seed, có thể bật `VITE_ENABLE_DEV_AUTH=true` và cấu hình UUID demo. Cơ chế này không xuất hiện trong production build và Backend production luôn từ chối header DEV.

```powershell
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run preview
```

`test:e2e` dùng Microsoft Edge đã cài trên Windows, tự chạy Backend ở cổng 8013 và Frontend ở cổng 5174. Smoke suite không ghi dữ liệu nghiệp vụ: kiểm tra health, public Specialty/Doctor discovery, protected-route redirect, token không nằm localStorage và form validation.

Phase 13 chuyển các feature page sang `React.lazy`/dynamic import. Production build trước tối ưu có một JS chunk 878,33 kB; sau tối ưu chunk lớn nhất còn 398,03 kB (giảm khoảng 54,7%) và không còn cảnh báo chunk >500 kB. Loading fallback được giữ trong lúc tải route; business behavior và API contract không đổi.

Preview dùng cổng 4173; nếu muốn gọi API trực tiếp từ preview, đặt `FRONTEND_ORIGIN=http://localhost:4173` ở backend rồi khởi động lại backend. Development dùng cổng 5173; không mở wildcard CORS.

Chỉ các giá trị công khai được đặt trong biến `VITE_*`. Không đặt Gemini API key, mật khẩu, JWT, model embedding hoặc DATABASE_URL vào frontend. Chat history chỉ nằm trong React state/request, tối đa 10 message và không được coi là MedicalRecord.

Chatbot gọi Backend qua `POST /api/v1/chat/messages` với cookie/CSRF hiện có và `use_rag=true`. UI hiển thị đúng metadata nguồn thực do Backend trả về, không tạo link giả. Khi retrieval/Gemini không khả dụng, UI hiển thị fallback an toàn và các chức năng Business MVP vẫn sử dụng được.

Khi Backend trả `risk_alert`, UI hiển thị cảnh báo khẩn riêng, các hành động an toàn và trạng thái handoff `PENDING`/`FAILED`. Cảnh báo này đến từ rule engine Backend độc lập Gemini và không phải chẩn đoán.

Voice dùng `navigator.mediaDevices.getUserMedia({ audio: true })` và `MediaRecorder`; sau STT, transcript được đặt vào cùng form text để user kiểm tra rồi gửi qua chat pipeline hiện có. TTS dùng `window.speechSynthesis`, có nút đọc/dừng và luôn fallback về text. Nếu permission, microphone, MediaRecorder, STT hoặc TTS lỗi, text chat vẫn hoạt động.

Staff/Admin Handoff UI kết nối `WS /api/v1/handoffs/ws`. Khi connect, reconnect hoặc nhận event, UI tải lại state authoritative bằng REST; WebSocket không lưu state và không thay thế PostgreSQL.

Khi Backend trả `CONFIRMATION_REQUIRED`, UI hiển thị bác sĩ/chuyên khoa/ngày/giờ/slot. Chỉ nút **Xác nhận đặt lịch** mới gọi `POST /api/v1/chat/bookings/confirm`; câu chat tự do không thực hiện mutation. Confirmation token chỉ giữ trong React state, không lưu localStorage hoặc đưa vào history.
