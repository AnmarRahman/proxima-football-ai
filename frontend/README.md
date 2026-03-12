# Frontend

This Next.js app reads prediction data through API routes:

- `GET /api/players` -> active and under-threshold player list from Supabase (`players` table)
- `GET /api/predictions/:playerId` -> latest prediction from `latest_player_predictions` view

If Supabase env vars are missing or query fails, routes fall back to local JSON in `public/data/predictions` when available.

## Admin dashboard

`/admin` provides a password-protected dashboard to:

- upload player JSON files to Supabase
- manually dispatch the GitHub workflow (`weekly-predictions.yml` by default)

Server routes used by the admin dashboard:

- `POST /api/admin/login`
- `POST /api/admin/logout`
- `GET /api/admin/session`
- `POST /api/admin/upload`
- `POST /api/admin/trigger`

## Environment variables

Copy `.env.example` to `.env.local` and fill values:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (optional for current server-routed setup)
- `SUPABASE_SERVICE_ROLE_KEY` (required for server API routes)
- `ADMIN_DASHBOARD_PASSWORD` (required for `/admin`)
- `ADMIN_SESSION_SECRET` (required for `/admin`)
- `GITHUB_ACTIONS_TOKEN` (required for manual workflow dispatch)
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `GITHUB_WORKFLOW_ID` (defaults to `weekly-predictions.yml`)
- `GITHUB_WORKFLOW_REF` (defaults to `main`)

## Run locally

```bash
npm install
npm run dev
```
