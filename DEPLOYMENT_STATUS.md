# Deployment status: NOT READY

Requested destination: entire website on Render Free, not a frontend-only deployment.

No Render service or public endpoint is configured by this repository. Do not treat a successful Next.js build as a working full-stack deployment.

Outstanding gates:

1. A reviewed single-origin frontend/API runtime and direct-access protection.
2. Isolated PostgreSQL 17 identity, TLS, least-privilege roles and separately approved revision0004/synthetic-fixture writes. Never use operational atlas or local databases.
3. Safe synthetic mail verification; Render Free blocks SMTP ports 25/465/587.
4. Synthetic-only served fixtures: shared frontend mock source currently contains real institution names with illustrative values. It is retained as application source in this private repository, not approved hosted factual data.
5. Linux locked build/startup, protected access, bounded resource use and actual browser auth/CSRF/session validation.

Do not enable public signup, experimental features, external AI, paid services or automatic startup migration/seed. No automatic deployment configuration is included. Source is intentionally missing private fixtures, frozen pilot data, reports and operator helpers. Existing development seed/package-data references do not authorize restoring excluded data.
