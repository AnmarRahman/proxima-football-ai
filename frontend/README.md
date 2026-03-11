# Frontend

This Next.js app now reads prediction data through API routes:

- `GET /api/players` -> active player list from Supabase (`players` table)
- `GET /api/predictions/:playerId` -> latest prediction from `latest_player_predictions` view

If Supabase env vars are missing or query fails, routes fall back to local JSON in `public/data/predictions` when available.

## Environment variables

Copy `.env.example` to `.env.local` and fill values:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (optional for current server-routed setup)
- `SUPABASE_SERVICE_ROLE_KEY` (required for server API routes)

## Run locally

```bash
npm install
npm run dev
```
