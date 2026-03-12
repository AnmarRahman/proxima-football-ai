param(
  [string]$VmHost = "10.0.0.220",
  [string]$VmUser = "anmarrahman",
  [string]$RemoteDir = "/home/anmarrahman/docker/proxima-football-ai"
)

$ErrorActionPreference = "Stop"
$remote = "$VmUser@$VmHost"

Write-Host "Uploading tracked repository files to $remote:$RemoteDir ..."

git archive --format=tar HEAD |
  ssh $remote "mkdir -p '$RemoteDir' && tar -xf - -C '$RemoteDir'"

if ($LASTEXITCODE -ne 0) {
  throw "Failed to upload files to VM."
}

Write-Host "Running remote Docker update..."
ssh $remote "bash '$RemoteDir/scripts/vm_update.sh' '$RemoteDir'"

if ($LASTEXITCODE -ne 0) {
  throw "Remote Docker update failed."
}

Write-Host "Deployment completed successfully."
