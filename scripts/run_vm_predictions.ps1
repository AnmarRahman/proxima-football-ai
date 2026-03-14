param(
  [string]$VmHost = "10.0.0.220",
  [string]$VmUser = "anmarrahman",
  [string]$RemoteDir = "/home/anmarrahman/docker/proxima-football-ai"
)

$ErrorActionPreference = "Stop"
$remote = "$VmUser@$VmHost"

ssh $remote "cd '$RemoteDir' && docker compose run --rm predictor"
if ($LASTEXITCODE -ne 0) {
  throw "Failed to run predictor on VM."
}

Write-Host "Prediction run completed."
