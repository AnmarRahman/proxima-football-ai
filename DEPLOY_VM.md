# VM Deployment (Docker)

Target VM path:

- `/home/anmarrahman/docker/proxima-football-ai`

Services:

- `app` (Next.js on port `4040`)
- `postgres` (`postgres:16-alpine`)
- `postgrest` (REST API over Postgres for the app)

## One-time setup on VM

```bash
mkdir -p /home/anmarrahman/docker/proxima-football-ai
```

## Deploy from local machine (PowerShell)

From repo root:

```powershell
./scripts/deploy_to_vm.ps1 -VmHost 10.0.0.220 -VmUser anmarrahman -RemoteDir /home/anmarrahman/docker/proxima-football-ai
```

This script:

1. archives tracked git files
2. uploads them to the VM target directory
3. runs remote container update script
4. forces `DATABASE_PROVIDER=postgres` for VM runtime
5. runs Postgres migrations and imports all player JSON files into Postgres

## Configure environment on VM

On first deploy, `.env` is created from `.env.docker.example`.

Edit on VM:

```bash
nano /home/anmarrahman/docker/proxima-football-ai/.env
```

At minimum set:

- `ADMIN_DASHBOARD_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `POSTGRES_PASSWORD`

## Docker commands on VM

```bash
cd /home/anmarrahman/docker/proxima-football-ai
docker compose ps
docker compose logs -f app
docker compose logs -f postgrest
```
