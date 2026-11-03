# Defense Notes

Các câu trả lời dưới đây mô tả implementation thực tế, không mở rộng thành claim lâm sàng hoặc production-scale chưa được kiểm chứng.

| Câu hỏi | Trả lời ngắn gọn để bảo vệ |
| --- | --- |
| Tại sao FastAPI? | Phù hợp Python AI stack, type validation qua Pydantic, OpenAPI tự động, async I/O và dễ debug trên Windows. Backend vẫn là Modular Monolith, không cần microservices. |
| Tại sao React? | Component/feature-based UI, hệ sinh thái TypeScript mạnh và phù hợp các màn hình nhiều trạng thái/role. |
| Tại sao PostgreSQL? | Cần transaction, FK, unique/check/index và concurrency correctness cho booking; đồng thời dùng pgvector trong cùng database. |
| Tại sao pgvector? | Tận dụng PostgreSQL đã dùng, giảm một database độc lập, giữ FK/transaction/data consistency và đủ cho quy mô đồ án. ChromaDB không phải implementation hiện tại. |
| Tại sao SQLAlchemy? | Mapping type-safe tương đối, transaction/session rõ, repository/service dễ test và dùng tốt với PostgreSQL/pgvector. |
| Tại sao Alembic? | Schema có lịch sử tái tạo/upgrade rõ ràng; không dùng `create_all` thay migration. Chain cuối là 0001→0004. |
| Tại sao UUID? | Tránh phụ thuộc sequence khi tạo dữ liệu giữa module/môi trường và khó đoán hơn ID tăng dần; `audit_logs` vẫn dùng bigint phù hợp log tuần tự. |
| Tại sao Patient không có table riêng? | Patient MVP chỉ cần dữ liệu User tối thiểu và role PATIENT. Tạo bảng riêng sẽ lặp dữ liệu mà chưa có thuộc tính chuyên biệt. |
| Tại sao Doctor có table riêng? | Doctor có specialty, license và professional profile riêng; đây là quan hệ domain thực, không chỉ role. |
| Tại sao MedicalRecord tách Appointment? | Appointment quản lý lịch/trạng thái; MedicalRecord là nội dung lâm sàng nhạy cảm chỉ xuất hiện sau COMPLETED. Tách bảng giữ cardinality 1:0..1 và quyền rõ. |
| Tại sao `SELECT FOR UPDATE`? | Hai request có thể cùng thấy slot AVAILABLE. Row lock serialize bước kiểm tra/ghi để chỉ một booking commit. |
| Tại sao advisory lock? | Schedule mới chưa có row ổn định để khóa; transaction advisory lock theo Doctor serialize kiểm tra overlap cho cùng bác sĩ. |
| Tại sao partial unique index? | Bảo đảm DB không cho nhiều Appointment chiếm cùng slot ở CONFIRMED/COMPLETED/NO_SHOW, trong khi CANCELLED cho phép rebook. |
| Tại sao ActorContext? | Tách identity/roles đã xác thực khỏi HTTP/JWT và truyền vào business service; tool/REST cùng reuse authorization, không tin identity do LLM gửi. |
| Tại sao JWT + refresh token? | Access token ngắn hạn phục vụ request; refresh session có hash/rotation/revocation/reuse detection để quản lý phiên mà không lưu token plaintext. |
| Tại sao HttpOnly cookie? | JavaScript không cần đọc token, giảm rủi ro token bị lấy trực tiếp qua XSS. Đổi lại phải bảo vệ CSRF. |
| Tại sao CSRF? | Browser tự gửi cookie; custom CSRF header + exact Origin/CORS ngăn website khác lợi dụng phiên để gửi state-changing request. |
| Tại sao BGE-M3? | Hỗ trợ đa ngôn ngữ, phù hợp tiếng Việt và cho embedding 1024 chiều; cùng model dùng cho document/query. |
| Tại sao VECTOR(1024)? | Đây là output dimension của BGE-M3 được chốt; schema và runtime kiểm tra cùng dimension để cosine search hợp lệ. |
| Tại sao Gemini? | API dễ tích hợp cho generation và structured tool proposal; key chỉ ở Backend, model configurable và provider failure được cô lập. |
| Tại sao RAG? | LLM không phải nguồn sự thật y khoa. RAG giới hạn câu trả lời bằng corpus được duyệt, hỗ trợ nguồn và fallback khi thiếu context. |
| Tại sao JSON dataset lớn? | Nguồn chính có cấu trúc anchor/positive/negative/meta và kích thước lớn; streaming JSON giúp xử lý không cần nạp toàn file vào RAM. |
| Tại sao không chỉ CSV? | Hệ thống vẫn hỗ trợ CSV, nhưng JSON giữ cấu trúc/metadata nguồn chính tốt hơn và phù hợp streaming schema của dataset. |
| Tại sao deduplicate? | Tránh cùng nội dung chiếm nhiều chunk, làm lệch retrieval, tăng embedding/storage/time và tạo nguồn lặp. |
| Tại sao exact retrieval làm baseline? | Dễ kiểm chứng, không phụ thuộc approximation/index tuning và tạo chuẩn công bằng trước khi đánh giá HNSW/hybrid/reranker. |
| Tại sao HNSW? | Giữ nguyên Hit/Recall/MRR của exact trên 50 query và có mean thấp nhất trong benchmark hiện tại; dùng index pgvector sẵn có. |
| Tại sao BM25/RRF? | Thử nghiệm bổ sung lexical retrieval và hợp nhất rank mà không cần score normalization. Kết quả hiện tại không tốt hơn nên không chọn mặc định. |
| Tại sao reranker? | Đánh giá khả năng sắp xếp candidate tốt hơn. V3 tăng Hit/Recall nhỏ nhưng CPU latency nhiều giây, nên giữ làm experiment. |
| Tại sao Tool Calling? | Dữ liệu bác sĩ/lịch/slot thay đổi động và phải qua quyền/rule; tool nối LLM với business service thật thay vì để model bịa dữ liệu. |
| Tại sao explicit booking confirmation? | Booking là mutation có hậu quả. Model chỉ chuẩn bị summary/token; user phải bấm xác nhận trước khi AppointmentService ghi dữ liệu. |
| Tại sao không cho AI đọc MedicalRecord? | Hồ sơ là dữ liệu nhạy cảm, không cần cho mục tiêu MVP và rủi ro privacy cao. Patient/Doctor truy cập trực tiếp qua API có quyền. |
| Tại sao Risk Alert rule-based? | Tín hiệu an toàn không được phụ thuộc duy nhất vào output tự do/không xác định của LLM. Rule chạy trước Gemini và có test cố định. |
| Tại sao WebSocket chỉ Handoff? | Chỉ Handoff cần notification/status gần thời gian thực. PostgreSQL/REST vẫn là nguồn sự thật; live Patient-Staff chat ngoài MVP. |
| Tại sao Voice push-to-talk? | Luồng đơn giản, user kiểm soát lúc ghi/dừng, dễ xử lý privacy/temp cleanup và phù hợp Windows demo hơn full-duplex streaming. |
| Tại sao dùng microphone browser có sẵn? | `getUserMedia`/`MediaRecorder` là API chuẩn, không cần driver/microphone ảo hay subsystem tùy chỉnh. |
| Tại sao faster-whisper? | Chạy local trên Windows, không gửi audio cho STT cloud và dễ tích hợp Python. Chất lượng tiếng Việt phụ thuộc model/hardware và đang là known limitation. |
| Tại sao không LangChain/LangGraph? | Pipeline không quá phức tạp; service/orchestrator tự triển khai giúp ít dependency, dễ debug, dễ kiểm soát privacy/tool authorization và tránh over-engineering. |
| Tại sao không ChromaDB? | PostgreSQL + pgvector đã đáp ứng vector search, transaction, FK và quản trị trong một hệ thống. ChromaDB sẽ thêm database/consistency/deployment burden không cần thiết cho quy mô đồ án. |

## Các câu hỏi dễ bị hỏi thêm

- **Có phải hệ thống chẩn đoán không?** Không. Chatbot cung cấp thông tin/định hướng, nguồn và escalation; kết luận MedicalRecord do Doctor nhập.
- **Đã ingest toàn bộ 1 GB chưa?** Chưa. Benchmark dùng large controlled subset 400 raw, 199 unique chunks mới, corpus DB 209 chunks.
- **Playwright đã test mọi vai trò chưa?** Chưa. 3 test chỉ là scoped release smoke. Multi-role/provider/WebSocket/microphone được kiểm tra ở các tầng khác và manual evidence.
- **Voice có hoàn hảo không?** Không. Pipeline chạy được nhưng độ chính xác STT tiếng Việt trên máy demo còn hạn chế và được đưa vào Future Improvement.
- **Vì sao không chọn V3 dù Recall cao hơn?** Chênh lệch 0.02 nhưng median CPU khoảng 8.2 giây; HNSW cân bằng chất lượng/độ trễ/tài nguyên tốt hơn cho demo.
- **Hệ thống có production-ready không?** READY cho phạm vi đồ án/demo có kiểm soát. Multi-instance rate limit, full dataset scaling, chuyên gia y khoa evaluation và deployment hardening sâu hơn vẫn là giới hạn.
