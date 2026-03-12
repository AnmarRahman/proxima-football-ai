# Frontend

This Next.js app supports three database providers:

- `postgres` (recommended for self-hosted Docker: via PostgREST)
- `supabase`
- `sqlite` (local/dev only)

Provider is selected with `DATABASE_PROVIDER`.

## API behavior

- `GET /api/players` -> active and under-threshold player list from configured provider
- `GET /api/predictions/:playerId` -> latest prediction from configured provider

If query fails, routes fall back to local JSON in `public/data/predictions` when available.

## Admin dashboard

`/admin` provides a password-protected dashboard to:

- upload player JSON files to the configured provider
- trigger GitHub workflow manually

Server routes:

- `POST /api/admin/login`
- `POST /api/admin/logout`
- `GET /api/admin/session`
- `POST /api/admin/upload`
- `POST /api/admin/trigger`

In SQLite mode, `/api/admin/trigger` is intentionally disabled.

## Environment variables

Copy `.env.example` to `.env.local` and fill values.

Core:

- `DATABASE_PROVIDER` -> `postgres`, `supabase`, or `sqlite`
- `ADMIN_DASHBOARD_PASSWORD`
- `ADMIN_SESSION_SECRET`

Postgres mode:

- `POSTGREST_URL`
- `POSTGREST_API_KEY` (optional)

SQLite mode:

- `SQLITE_DATABASE_PATH`

Supabase mode:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (optional)
- `SUPABASE_SERVICE_ROLE_KEY`

GitHub trigger:

- `GITHUB_ACTIONS_TOKEN`
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `GITHUB_WORKFLOW_ID`
- `GITHUB_WORKFLOW_REF`

## Run locally

```bash
npm install
npm run dev
```
