# Screenshot Checklist — Manual Capture Required

No screenshot is fabricated or treated as evidence without a real running UI/session. Capture these images manually on the final demo machine after seeding synthetic data and setting demo passwords interactively. Do not show `.env`, browser cookie values, database passwords, API keys, refresh tokens, terminal secrets or real patient data.

Use one consistent browser size, zoom 100%, synthetic names only, and crop irrelevant desktop content. Retake any image with a visible error unrelated to the demonstrated case.

| # | Screen / evidence | Required state | Status |
| ---: | --- | --- | --- |
| 01 | Register | Patient form with required phone and safe validation | MANUAL CAPTURE REQUIRED |
| 02 | Login | login form; no credentials visible after submission | MANUAL CAPTURE REQUIRED |
| 03 | Specialty | active specialty list | MANUAL CAPTURE REQUIRED |
| 04 | Doctor | doctor list filtered by specialty | MANUAL CAPTURE REQUIRED |
| 05 | Slots | selected doctor/date with AVAILABLE slots | MANUAL CAPTURE REQUIRED |
| 06 | Booking | confirmation/success and selected slot | MANUAL CAPTURE REQUIRED |
| 07 | Patient Appointment | CONFIRMED appointment list/detail | MANUAL CAPTURE REQUIRED |
| 08 | Doctor workflow | assigned appointment and COMPLETED action | MANUAL CAPTURE REQUIRED |
| 09 | MedicalRecord form | four clinical fields; synthetic content | MANUAL CAPTURE REQUIRED |
| 10 | Patient history | read-only history/detail | MANUAL CAPTURE REQUIRED |
| 11 | Document approval | APPROVED document and ingestion status | MANUAL CAPTURE REQUIRED |
| 12 | RAG ingestion status | COMPLETED/status/chunk summary if UI exposes it | MANUAL CAPTURE REQUIRED; omit if UI does not expose summary |
| 13 | Chatbot text | safe Gemini answer | MANUAL CAPTURE REQUIRED |
| 14 | RAG sources | answer with actual source metadata | MANUAL CAPTURE REQUIRED |
| 15 | Tool result | doctor or slot result from business data | MANUAL CAPTURE REQUIRED |
| 16 | AI booking confirmation | summary before explicit Confirm | MANUAL CAPTURE REQUIRED |
| 17 | Risk Alert | deterministic warning and non-diagnostic wording | MANUAL CAPTURE REQUIRED |
| 18 | Handoff | PENDING/IN_PROGRESS state in user and Staff views | MANUAL CAPTURE REQUIRED |
| 19 | Voice | recording state, editable transcript or clear fallback error | MANUAL CAPTURE REQUIRED |
| 20 | Swagger/health (optional) | health 200 and API docs; no secret response | MANUAL CAPTURE REQUIRED |

## Evidence labeling

Name images consistently, for example `01-register.png`, `02-login.png`, … `19-voice.png`. In the final thesis, captions should describe only what the screenshot proves. A Voice screenshot proves UI/pipeline state, not STT accuracy across all hardware.

