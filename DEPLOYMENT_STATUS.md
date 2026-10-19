# Offline-only $0 hackathon deployment candidate

Not pushed, deployed or approved for publication. Replaces the prior two-service API demo scope only with new explicit approval.

- Private repository: jekyhasanshuvo-alt/atlas-staging; branch hackathon-demo.
- Only service proposed now: atlas-staging-web, workspace tea-dbamcgs9v7es739371g0, Singapore, Free $0, manual deployments.
- atlas-staging-api is deferred and must not be created or deployed under this scope.
- Existing atlas-staging service must not be repurposed; production, Neon and operational databases remain untouched.
- Node 24.16.0, repository root. Build: `npm ci && npm run build`.
- Start: `npm run start -- --hostname 0.0.0.0 --port $PORT`. Health: `/`.
- Build and runtime: NEXT_PUBLIC_ATLAS_OFFLINE_DEMO=true, NEXT_PUBLIC_ATLAS_DATA_MODE=demo,
  NEXT_PUBLIC_ATLAS_API_BASE_URL=/api/v1, NEXT_PUBLIC_ATLAS_STAGING_DEMO=false, NEXT_TELEMETRY_DISABLED=1.
- Server runtime: ATLAS_STAGING_PROXY_ENABLED=false. No database URL, upstream origins, transport/mailbox keys or other secrets.
- No env groups, analytics, custom domains, disks, add-ons, paid upgrades, card entry or keep-alive requests.
- Creation may trigger the first deploy: creation and initial deployment require one explicit revised approval tied to the new commit.
- Backend API proxy returns 404 without fetching. Direct account/API clients also refuse requests.
- Account/profile/signup/login/email/recovery/AI/application forms are unavailable; no account collection or database access.
- Catalogs are empty. Financial calculations use hypothetical local inputs; no factual institution or award data.
- Demo inputs live in memory only, reset on reload and never read old localStorage profile values.
- Free-tier sleep, cold starts and shared quotas apply; no uptime guarantee or automatic paid conversion.
- On target/plan/commit/env/security mismatch stop. No fallback to API mode or old main.
- Hosted verification after approval: HTTPS, demo labeling, dashboard/catalog navigation, financial input recalculation/reset,
  account pages without forms, API 404, no auth cookies, no backend/database requests.
- Rollback after a failed deployment: stop and report; suspend only the newly created service if explicitly authorized.
  Do not deploy the old backend-connected configuration or change C1/C2/PUBLIC privileges.
