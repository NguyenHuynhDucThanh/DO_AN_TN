# Sơ đồ kiến trúc cuối

Đề tài: **Xây dựng hệ thống y tế tích hợp chatbot hỗ trợ tư vấn, tra cứu và đặt lịch hẹn.**

Baseline: SRS v1.1. Các sơ đồ dưới đây phản ánh implementation cuối Phase 13/14; không có ChromaDB, Redis, Celery, Docker, microservices hoặc LangChain/LangGraph trong core.

## 1. System Architecture

```mermaid
flowchart TB
    U[Patient / Doctor / Staff / Admin] --> B[Browser]
    B --> FE[React + TypeScript + Vite + MUI]
    FE -->|REST + HttpOnly cookie + CSRF| API[FastAPI Modular Monolith]
    FE <-->|Handoff notification/status| WS[FastAPI WebSocket]
    WS --> API
    API --> AUTH[Auth + ActorContext + RBAC]
    API --> BIZ[Business Services]
    API --> AI[Chat Orchestrator]
    API --> VOICE[Voice STT]
    AUTH --> DB[(PostgreSQL 18 + pgvector)]
    BIZ --> DB
    AI --> RAG[RAG Service]
    AI --> TOOLS[Tool Layer]
    AI --> RISK[Rule-based Risk Alert]
    RAG --> DB
    TOOLS --> BIZ
    RISK --> BIZ
    AI --> GEMINI[Gemini API]
    VOICE --> WHISPER[faster-whisper]
```

## 2. Frontend / Backend Architecture

```mermaid
flowchart LR
    subgraph Frontend
        ROUTER[React Router + lazy pages]
        UI[MUI pages/components]
        FORM[React Hook Form + Zod]
        QUERY[TanStack Query]
        AXIOS[Axios client]
        ROUTER --> UI
        UI --> FORM
        UI --> QUERY
        QUERY --> AXIOS
    end
    subgraph Backend
        R[Router]
        S[Service]
        REP[Repository / Data Access]
        ORM[SQLAlchemy 2]
        R --> S --> REP --> ORM
    end
    AXIOS -->|REST| R
    ORM --> PG[(PostgreSQL + pgvector)]
```

## 3. ERD cuối

```mermaid
erDiagram
    USERS ||--o{ USER_ROLES : receives
    ROLES ||--o{ USER_ROLES : grants
    USERS ||--o{ REFRESH_SESSIONS : owns
    USERS ||--o| DOCTORS : has_profile
    SPECIALTIES ||--o{ DOCTORS : classifies
    DOCTORS ||--o{ DOCTOR_SCHEDULES : publishes
    DOCTOR_SCHEDULES ||--o{ SCHEDULE_SLOTS : contains
    USERS ||--o{ APPOINTMENTS : patient_books
    SCHEDULE_SLOTS ||--o{ APPOINTMENTS : receives_history
    APPOINTMENTS ||--o| MEDICAL_RECORDS : has
    USERS ||--o{ MEDICAL_RECORDS : creates_updates
    USERS ||--o{ DOCUMENTS : uploads_approves
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : splits_into
    USERS ||--o{ HANDOFF_REQUESTS : requests_handles
    USERS ||--o{ AUDIT_LOGS : acts

    APPOINTMENTS {
        uuid id PK
        uuid patient_id FK
        uuid schedule_slot_id FK
        varchar status
    }
    MEDICAL_RECORDS {
        uuid id PK
        uuid appointment_id FK,UK
        text symptoms
        text clinical_notes
        text doctor_conclusion
        text follow_up_instructions
        uuid created_by FK
        uuid updated_by FK
    }
    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        int chunk_index UK
        text content
        vector_1024 embedding
        jsonb metadata
    }
```

ERD chi tiết và chính sách FK/xóa nằm trong `database-design.md`; Data Dictionary nằm trong `data-dictionary.md`. Patient không có bảng riêng: Patient là `User + PATIENT role`. Doctor có bảng riêng vì cần specialty, license và professional profile. MedicalRecord liên hệ Patient qua Appointment.

## 4. Use Case Diagram

```mermaid
flowchart LR
    P[Patient] --> REG[Register / Login]
    P --> DISC[Browse Specialty / Doctor / Slot]
    P --> BOOK[Book / Cancel Appointment]
    P --> HIST[Read own MedicalRecord]
    P --> CHAT[Chat / RAG / Tools / Voice]
    P --> HO[Create Handoff]
    D[Doctor] --> SCH[Manage own Schedule / Slot]
    D --> APT[View assigned Appointment]
    D --> MR[Complete visit / Create or update MedicalRecord]
    S[Staff] --> COORD[Coordinate Schedule / Appointment]
    S --> HOP[Process Handoff]
    A[Admin] --> MASTER[Manage Specialty / Doctor]
    A --> DOC[Approve Document / Ingest status]
    A --> HOP
```

## 5. Authentication Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as Auth Router/Service
    participant DB as PostgreSQL
    B->>A: Login email + password + Origin
    A->>DB: Load ACTIVE user (case-insensitive email)
    A->>A: Argon2 verify
    A->>DB: Store refresh token hash/session family
    A-->>B: HttpOnly access/refresh cookies + CSRF token
    B->>A: State-changing request + CSRF header
    A->>A: Verify JWT, Origin, CSRF
    A->>DB: Reload user and roles
    A-->>B: ActorContext-authorized response
    B->>A: Refresh
    A->>DB: Rotate/revoke old refresh session
    A-->>B: New cookie pair
```

## 6. Booking Sequence

```mermaid
sequenceDiagram
    participant P as Patient
    participant API as AppointmentService
    participant DB as PostgreSQL
    P->>API: Book available slot
    API->>DB: BEGIN + SELECT slot FOR UPDATE
    API->>DB: Verify AVAILABLE and occupied-slot invariant
    API->>DB: Insert CONFIRMED Appointment
    API->>DB: Update slot to BOOKED
    API->>DB: COMMIT
    API-->>P: Appointment created
    Note over API,DB: Partial unique index covers CONFIRMED, COMPLETED, NO_SHOW
```

## 7. MedicalRecord Sequence

```mermaid
sequenceDiagram
    participant D as Assigned Doctor
    participant API as MedicalRecordService
    participant DB as PostgreSQL
    participant P as Patient
    D->>API: Create/update examination result
    API->>DB: Verify ActorContext + Doctor ownership
    API->>DB: Verify Appointment COMPLETED
    API->>DB: Enforce UNIQUE appointment_id
    API->>DB: Save content + updated_at/updated_by
    API->>DB: Write metadata-only audit
    API-->>D: Saved
    P->>API: Read own history/detail
    API->>DB: Verify Appointment.patient_id
    API-->>P: Read-only MedicalRecord
```

## 8. Document Ingestion Pipeline

```mermaid
flowchart LR
    SRC[JSON / CSV / text PDF / DOCX] --> LOAD[Streaming/format loader]
    LOAD --> NORM[Normalize Unicode/content]
    NORM --> DEDUP[Deduplicate]
    DEDUP --> CHUNK[Chunk]
    CHUNK --> EMB[BGE-M3 embedding]
    EMB --> VEC[VECTOR 1024]
    VEC --> PG[(document_chunks + pgvector)]
    GOV[Admin APPROVED only] --> LOAD
```

JSON is the primary large dataset format. CSV/PDF/DOCX remain supported for other sources. PDF requires extractable text; OCR is outside RAG V1.

## 9. RAG Pipeline

```mermaid
flowchart LR
    Q[Question] --> E[BGE-M3 query vector]
    E --> RET[HNSW dense Top-K]
    DB[(APPROVED + COMPLETED document_chunks)] --> RET
    RET --> CTX[Context + source metadata]
    CTX --> G[Gemini]
    G --> SAFE[Safety formatting]
    SAFE --> ANS[Answer + sources]
    RET -->|empty / failure| FB[Controlled no-context fallback]
```

Runtime default is `hnsw_dense`; `exact_dense` is baseline/fallback. `hybrid_rrf` and `hybrid_rerank` are retained experiments, not default. MedicalRecord is not a corpus source.

## 10. Tool Calling Flow

```mermaid
flowchart LR
    M[User message] --> O[Chat Orchestrator]
    O --> G[Gemini structured tool proposal]
    G --> V[Tool registry + Pydantic validation]
    V --> A[ActorContext / role / object checks]
    A --> S[Existing Business Service]
    S --> DB[(PostgreSQL)]
    DB --> R[Tool result]
    R --> O
    O --> F[Final response]
    V -->|booking intent| C[Confirmation token + summary]
    C -->|user explicit confirm| S
```

The LLM never receives authority to access ORM/SQL directly and cannot supply trusted identity/role.

## 11. Risk Alert Flow

```mermaid
flowchart LR
    IN[Input] --> RULE[Deterministic risk rules]
    RULE -->|trigger| WARN[Fixed safety warning]
    WARN --> HO[HandoffService urgent ticket]
    HO --> DB[(PostgreSQL)]
    RULE -->|no trigger| ROUTE[Knowledge / business / booking routing]
    ROUTE --> OUT[Gemini / RAG / Tools]
    OUT --> FORMAT[Final safety formatting]
```

Risk Alert runs before Gemini so the LLM cannot hide the safety signal. It is escalation support, not diagnosis or prescription.

## 12. Handoff WebSocket Flow

```mermaid
sequenceDiagram
    participant U as User/Chatbot
    participant REST as Handoff REST Service
    participant DB as PostgreSQL
    participant WS as WebSocket Hub
    participant S as Staff/Admin UI
    U->>REST: Create handoff
    REST->>DB: Persist PENDING request
    REST->>WS: Publish metadata event
    WS-->>S: Notification/status
    S->>REST: Reload authoritative state
    REST->>DB: Read/update workflow
    REST-->>S: PENDING / IN_PROGRESS / RESOLVED
    Note over S,DB: If WebSocket fails, REST/DB workflow remains available
```

There is no live Patient-Staff chat in MVP.

## 13. Voice Pipeline

```mermaid
flowchart LR
    MIC[Physical microphone] --> MEDIA[getUserMedia + MediaRecorder]
    MEDIA --> AUDIO[Recorded audio blob]
    AUDIO --> API[FastAPI voice endpoint]
    API --> TMP[Temporary file]
    TMP --> STT[faster-whisper Vietnamese STT]
    STT --> CLEAN[Cleanup temporary file]
    STT --> TXT[Editable transcript]
    TXT --> CHAT[Existing text Chat pipeline]
    CHAT --> RESP[Text response]
    RESP --> TTS[Browser SpeechSynthesis optional]
```

Voice is an input/output layer, not a second chatbot. Text remains the fallback. Vietnamese recognition quality varies by hardware/environment and is a recorded known limitation.
