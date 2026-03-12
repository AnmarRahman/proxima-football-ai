param(
  [string]$VmHost = "10.0.0.220",
  [string]$VmUser = "anmarrahman",
  [string]$RemoteDir = "/home/anmarrahman/docker/proxima-football-ai"
)

$ErrorActionPreference = "Stop"
$remote = "$VmUser@$VmHost"
$tempTar = Join-Path $env:TEMP ("proxima-deploy-" + [guid]::NewGuid().ToString("N") + ".tar")
$remoteTar = "/tmp/proxima-deploy.tar"

try {
  Write-Host "Creating git archive..."
  git archive --format=tar --output="$tempTar" HEAD
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create git archive."
  }

  Write-Host ("Uploading archive to {0}:{1} ..." -f $remote, $RemoteDir)
  $scpTarget = "{0}:{1}" -f $remote, $remoteTar
  scp "$tempTar" "$scpTarget"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload archive to VM."
  }

  Write-Host "Extracting archive on VM..."
  ssh $remote "mkdir -p '$RemoteDir' && tar -xf '$remoteTar' -C '$RemoteDir' && rm -f '$remoteTar'"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to extract archive on VM."
  }

  Write-Host "Running remote Docker update..."
  ssh $remote "sed -i 's/\r$//' '$RemoteDir/scripts/vm_update.sh' && bash '$RemoteDir/scripts/vm_update.sh' '$RemoteDir'"
  if ($LASTEXITCODE -ne 0) {
    throw "Remote Docker update failed."
  }

  Write-Host "Deployment completed successfully."
}
finally {
  if (Test-Path $tempTar) {
    Remove-Item -Force $tempTar
  }
}
