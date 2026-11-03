# Final Demo Script

Target duration: 15–20 minutes. Use synthetic data only. Do not type or reveal a password/API key on the projected screen.

## Pre-demo preparation

1. Start PostgreSQL Windows Service and verify `scripts/check_database.py`.
2. Run `alembic upgrade head` and `seed_demo.py`.
3. Set Patient/Doctor/Staff/Admin demo passwords through `set_demo_password.py` hidden prompts. Never store them in this file.
4. Start Backend on `127.0.0.1:8000`, Frontend on `localhost:5173`.
5. Verify health, login, one available slot, Gemini quota/key, an APPROVED+COMPLETED RAG document, Handoff and browser microphone permission.
6. Keep separate browser profiles/incognito windows for Patient, Doctor and Staff/Admin, or log out between roles.
7. Keep the direct Business MVP path ready even if AI/external services fail.

## Main flow

| Step | Actor | Action | Expected evidence / narration |
| ---: | --- | --- | --- |
| 1 | Patient | Login | HttpOnly-cookie session restored; no token in localStorage |
| 2 | Patient | Browse Specialty | active master data from PostgreSQL |
| 3 | Patient | Filter/select Doctor | Doctor data linked to one primary Specialty |
| 4 | Patient | View available slots | dynamic business query, not RAG |
| 5 | Patient | Book one slot | Backend locks/rechecks slot; Appointment CONFIRMED; slot BOOKED |
| 6 | Doctor | Login and open assigned Appointment | object-level authorization |
| 7 | Doctor | Mark Appointment COMPLETED | valid transition; occupied slot remains historical |
| 8 | Doctor | Create MedicalRecord | COMPLETED-only, assigned Doctor, one record per Appointment |
| 9 | Patient | Open medical history/detail | own-read and read-only; Staff/Admin not granted clinical access |
| 10 | Patient | Ask Gemini a general health question | safe text answer; Business MVP remains independent |
| 11 | Patient | Ask “đau họng và hơi sốt thì nên làm gì” | RAG answer uses cautious wording |
| 12 | Patient | Expand/show sources | real source metadata from retrieved chunks |
| 13 | Patient | Ask to find a Doctor/slot | Tool Layer queries existing Business Services/PostgreSQL |
| 14 | Patient | Request booking through chat | UI shows summary and `CONFIRMATION_REQUIRED`; no write yet; click Confirm to call AppointmentService |
| 15 | Patient | Enter a configured urgent-risk demo phrase | deterministic Risk Alert appears before Gemini; no diagnosis; Handoff offered/created |
| 16 | Staff | Open Handoff | REST record persists; WebSocket notifies/status-updates; reload reads PostgreSQL |
| 17 | Patient | Record a short Vietnamese sentence | microphone → MediaRecorder → faster-whisper → editable transcript → existing Chat pipeline; explain current accuracy limitation |

## Suggested RAG queries

- “nay mệt với sổ mũi” — historically retrieved relevant throat/sinus material.
- “đau họng và hơi sốt thì nên làm gì” — historically retrieved clearly related throat material.
- “hay chóng mặt khi đứng lên” — use only to explain a known limitation: results may be mixed/overbroad; do not present as a diagnosis.

Do not claim these queries prove clinical correctness. They demonstrate retrieval behavior on a controlled corpus.

## Fallback plan

| Failure | What to show | What not to claim |
| --- | --- | --- |
| Gemini network/quota/API error | controlled chat error/fallback; continue Auth/Doctor/Schedule/Appointment/MedicalRecord | do not retry indefinitely or expose provider details |
| RAG unavailable/empty | no-context cautious fallback; direct business search still works | do not invent sources |
| Voice unavailable/inaccurate | type/edit transcript manually; text chat remains available | do not call inaccurate STT a successful quality result |
| WebSocket unavailable | reload Handoff through REST; PostgreSQL record remains | do not claim live status received |
| Tool failure/booking conflict | clear failure/409 and choose another slot | do not bypass AppointmentService |
| Browser/microphone permission denied | show clear permission error and text fallback | do not fake microphone evidence |

## Closing message

The thesis demonstrates a complete controlled Business MVP and an integrated AI support layer. The AI retrieves governed public/demo knowledge and invokes authorized business services, but it does not diagnose, prescribe, read MedicalRecord content or bypass explicit booking confirmation.
