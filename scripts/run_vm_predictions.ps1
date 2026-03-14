param(
  [string]$VmHost = "10.0.0.220",
  [string]$VmUser = "anmarrahman",
  [string]$RemoteDir = "/home/anmarrahman/docker/proxima-football-ai"
)

$ErrorActionPreference = "Stop"
$remote = "$VmUser@$VmHost"

ssh $remote "cd '$RemoteDir' && docker compose run --rm predictor bash -lc 'set -euxo pipefail; pip install --no-cache-dir -r backend/requirements.txt; python -u backend/python/main.py --data-source db --output-target db --all-active --epochs 120 --batch-size 16 --window-size 4 --retirement-age 40 --run-type manual --triggered-by vm-script --model-version gru-v2'"
if ($LASTEXITCODE -ne 0) {
  throw "Failed to run predictor on VM."
}

ssh $remote "cd '$RemoteDir' && docker compose exec -T postgres psql -U proxima -d proxima_ai -c 'select count(*) as player_predictions from player_predictions;'"
if ($LASTEXITCODE -ne 0) {
  throw "Predictor ran but failed to verify player_predictions count."
}

Write-Host "Prediction run completed."
