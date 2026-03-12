# VM Deployment (Docker)

Target VM path:

- `/home/anmarrahman/docker/proxima-football-ai`

Services:

- `app` (Next.js on port `4040`)
- `postgres` (`postgres:16-alpine`)

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

## Configure environment on VM

On first deploy, `.env` is created from `.env.docker.example`.

Edit on VM:

```bash
nano /home/anmarrahman/docker/proxima-football-ai/.env
```

At minimum set:

- `ADMIN_DASHBOARD_PASSWORD`
- `ADMIN_SESSION_SECRET`

## Docker commands on VM

```bash
cd /home/anmarrahman/docker/proxima-football-ai
docker compose ps
docker compose logs -f app
```
