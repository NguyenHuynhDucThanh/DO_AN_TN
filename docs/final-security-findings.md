# Final Security Findings

Ngày audit cuối: 02/11/2026.

## Status

- Open Critical: **0**.
- Open High: **0**.
- Production npm vulnerabilities: **0**.
- Python known vulnerabilities from `pip-audit`: **0**.
- Accepted Moderate: **12**, limited to ESLint/minimatch development tooling; npm's available full fix requires a breaking forced toolchain change. This does not ship in the browser production bundle.

## Findings and actions

| Severity | Finding | Action / evidence | Final status |
| --- | --- | --- | --- |
| HIGH | `follow-redirects` 1.16.0–1.16.1 advisory appeared after Phase 13 checkpoint | `npm audit fix` updated lockfile to 1.16.2; full Frontend regression and Playwright rerun | FIXED |
| HIGH | Historical PyJWT/python-multipart advisories | pinned PyJWT 2.15.0 and python-multipart 0.0.31; `pip-audit` clean | FIXED Phase 13 |
| MEDIUM | Application abuse/resource endpoints lacked rate limit | bounded hashed in-process limiter for auth/chat/voice/ingestion; 429 + Retry-After; production guard | FIXED Phase 13 |
| MEDIUM | CSV could retain `negative` metadata | excluded and regression-tested | FIXED Phase 13 |
| MEDIUM | ESLint dependency path uses minimatch 10.2.6 under current advisory | no non-breaking resolution offered; runtime audit is clean; do not use `npm audit fix --force` before demo | ACCEPTED dev-tool limitation |
| LOW | Limiter is per process | suitable for single-instance thesis/demo; use platform/reverse-proxy shared limiting when multi-instance | ACCEPTED deployment limitation |
| LOW | Unexpected errors/security headers | sanitized JSON 500; nosniff/frame/referrer/permissions headers; HSTS production | FIXED Phase 13 |

## Secret and privacy audit

- `.env` and `.env.*` are ignored; `.env.example` is explicitly allowed and contains placeholders only.
- `GEMINI_API_KEY`, database password and JWT secret stay Backend/local; no secret belongs in `VITE_*`.
- Pattern scan found only deliberate synthetic credentials in tests, the development-only JWT sentinel rejected by production configuration, and placeholders/documentation. No real credential was identified.
- The repository currently has no commit history containing project files (working tree is untracked), so historical secret exposure cannot be proven or disproven from Git history. Before the first commit, re-run the scan and review staged content.
- If a real secret was ever shared or committed elsewhere, rotate/revoke it; deleting a file is not sufficient.
- MedicalRecord content is excluded from Documents/DocumentChunks, RAG, Gemini, Tool Calling, Risk Alert input, Voice context and clinical audit payloads.
- Demo data uses synthetic `.invalid` accounts; demo passwords are set interactively through `set_demo_password.py`, not stored in Git/report.

## Production configuration requirements

- HTTPS frontend origin and `COOKIE_SECURE=true`.
- Exact CORS origin with credentials; no wildcard.
- Unique random `JWT_SECRET`; `DEV_AUTH_ENABLED=false`.
- Rate limiting enabled; add shared edge limiting when running more than one Backend instance.
- Store Gemini/database credentials in the hosting platform secret manager/environment, never in Frontend or committed files.

