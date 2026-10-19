# Deployment: awaiting exact approval

No Render service or hosted test is represented as complete by this source.
Workspace: My Workspace (tea-dbamcgs9v7es739371g0). Region: Singapore.
Proposed names: atlas-staging-api and atlas-staging-web, each Free, auto-deploy OFF.
Actual assigned HTTPS origins must be confirmed before secret configuration and deployment.

| Service | Root | Build | Start |
| --- | --- | --- | --- |
| web (Node 24.16.0) | repository root | `npm ci && npm run build` | `npm run start -- --hostname 0.0.0.0 --port $PORT` |
| api (Python 3.14.5) | backend | `pip install --requirement requirements.lock` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log` |

Backend health: /api/v1/health (no DB). Readiness: /api/v1/ready (transport key required, DB SELECT 1).
No native Linux installation/startup has yet been verified. Existing locks are unchanged.
Use the native Node runtime; do not deploy as a static site. Keep the build in API mode.

Frontend public build settings: NEXT_PUBLIC_ATLAS_DATA_MODE=api,
NEXT_PUBLIC_ATLAS_API_BASE_URL=/api/v1, NEXT_PUBLIC_ATLAS_STAGING_DEMO=true.
Frontend server settings: ATLAS_STAGING_PROXY_ENABLED=true,
ATLAS_STAGING_FRONTEND_ORIGIN, ATLAS_STAGING_BACKEND_ORIGIN, ATLAS_STAGING_TRANSPORT_KEY.
The last three origins/key must match the approved services; the key is secret.
NEXT_TELEMETRY_DISABLED=1; Node pin supplied by .node-version.

Backend: ATLAS_ENVIRONMENT=production (secure runtime mode; isolated staging data),
ATLAS_STAGING_DEMO=true, ATLAS_COOKIE_SECURE=true, ATLAS_EMAIL_ADAPTER=staging_sink,
ATLAS_FRONTEND_URL and JSON ATLAS_CORS_ORIGINS match the single frontend HTTPS origin;
JSON ATLAS_TRUSTED_HOSTS contains only the assigned backend hostname.
ATLAS_POOL_SIZE=1, ATLAS_POOL_MAX_OVERFLOW=0, ATLAS_SESSION_HOURS=1,
ATLAS_VERIFICATION_MINUTES=30, ATLAS_RESET_MINUTES=15,
ATLAS_ENABLE_DEMO_SEED=false, ATLAS_EXPERIMENTAL_FOUNDATION=false,
ATLAS_EXPERIMENTAL_JOURNEY=false, ATLAS_EXPERIMENTAL_ADVISOR=false,
ATLAS_PUBLISHED_SCHOLARSHIPS={}.
JSON ATLAS_STAGING_SYNTHETIC_EMAILS contains only atlas-demo-a@example.com and atlas-demo-b@example.com.
ATLAS_STAGING_DATABASE_WRITES_ENABLED=false and ATLAS_STAGING_SIGNUP_ENABLED=false initially.
Account reads also stay blocked because they can update sessions/rate limits.
Secrets: ATLAS_DATABASE_URL, ATLAS_STAGING_TRANSPORT_KEY, ATLAS_STAGING_MAILBOX_KEY.
ATLAS_STAGING_DATABASE_HOST must be the exact approved direct Neon endpoint.
Use atlas_staging_app in atlas_staging with sslmode=verify-full and sslrootcert pointing
to certifi's installed CA bundle (`python -m certifi` identifies the path); no owner credentials.
No database URL, password or real transport/mailbox key has been created by this preparation.

Mail never leaves the process: max16 entries, 10min TTL, consume once, erased on restart.
Only an operator with BOTH server transport and distinct mailbox keys may POST
/api/v1/staging-mail/consume directly, with exact frontend Origin and X-Atlas-CSRF.
The frontend proxy never exposes this route. Retrieve links privately; never paste tokens in reports.
Verification/reset still consume the existing one-time token and enforce normal expiry.
Do not allow real-user signup. After a separately approved two-account setup, close signup again.

Local checks: `npx vitest run tests/staging-proxy.test.ts tests/financial-scenarios.test.ts`;
`python -m pytest backend/tests_offline/test_staging_demo.py -q` (mock persistence, no DB);
`npm run typecheck`. The offline test intentionally runs in its own process and forbids PG connects.
Do not run operational DB suites. Linux hosted startup and real authentication remain pending.

Exposure: public fictional frontend, no platform-wide password protection; protected account pages;
public backend health only, all other backend paths require the transport secret.
Do not put any real student data in this internet-accessible demo.
No external AI, Advisor backend, RAG, imports, review actions, or account export/delete proxy routes.

Gate A: exact two Free resources/commands/exposure. Gate B: exact reviewed commit/private push/deploy.
Gate C: new role/grants and any synthetic-account lifecycle writes. Old schema approval is consumed.
Do not enable writes before Gate C. No catalog fixtures are included or authorized.
Two always-running services exceed the shared 750h monthly allowance. No keep-alive pings.
Keep no payment card, $0 pipeline limit, manual deploys, no paid resources/disks/domains/add-ons.
If limits are reached, accept suspension; never upgrade automatically.
On security failure suspend exposure. Roll back only to a separately reviewed safe commit;
the earlier baseline lacks these staging protections. Never automatically downgrade the database.
