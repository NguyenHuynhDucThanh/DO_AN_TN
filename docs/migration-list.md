# Final Migration List

| Order | Revision | Purpose | Final state |
| ---: | --- | --- | --- |
| 1 | `0001_enable_pgvector` | Enable PostgreSQL `vector` extension | Applied |
| 2 | `0002_create_business_schema` | Create identity, care, appointment, MedicalRecord, Document/DocumentChunk, Handoff and audit schema; `VECTOR(1024)` | Applied |
| 3 | `0003_phase2_invariants` | Strengthen constraints/indexes including occupied-slot and schema invariants | Applied |
| 4 | `0004_add_json_document_type` | Add governed JSON/JSONL document source type for RAG ingestion | Applied, current head |

Final verification on 02/11/2026:

- `alembic current`: `0004_add_json_document_type (head)`.
- `alembic heads`: one head, `0004_add_json_document_type`.
- `alembic check`: no new upgrade operations.
- PostgreSQL 18.6 and pgvector 0.8.7 runtime check: PASS.
- No Phase 13 or Phase 14 migration was needed.
- Historical applied revisions were not edited, squashed or deleted.
