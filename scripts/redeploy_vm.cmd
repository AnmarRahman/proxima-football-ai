@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%deploy_to_vm.ps1"
if errorlevel 1 (
  exit /b %errorlevel%
)

echo Redeploy finished.
