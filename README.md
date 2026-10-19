# Atlas staging source

Private code-only staging snapshot of the Atlas student intelligence application.

- Frontend: Next.js / React at repository root; `npm ci`, `npm run build`.
- API: FastAPI in `backend/`; dependencies in `backend/requirements.lock`.
- PostgreSQL schema baseline: active Alembic revisions 0001 through 0004.

This source snapshot is not a deployment-ready hosted environment. Read DEPLOYMENT_STATUS.md before creating services. No database or mail credentials are included. No license or public redistribution permission is granted here.
