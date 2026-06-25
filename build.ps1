# build.ps1 — Builds SkillIssueRacing into dist/SkillIssueRacing/
# Run from repo root: .\build.ps1

Set-StrictMode -Off
$ErrorActionPreference = "Stop"

Write-Host "`n=== Step 1: Build React frontend ===" -ForegroundColor Cyan
Set-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host "npm build failed" -ForegroundColor Red; exit 1 }
Set-Location ..

Write-Host "`n=== Step 2: Package with PyInstaller ===" -ForegroundColor Cyan
pyinstaller skillissue.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Host "PyInstaller failed" -ForegroundColor Red; exit 1 }

Write-Host "`n=== Build complete ===" -ForegroundColor Green
Write-Host "Output: dist\SkillIssueRacing\SkillIssueRacing.exe" -ForegroundColor Green
Write-Host "Test it: .\dist\SkillIssueRacing\SkillIssueRacing.exe" -ForegroundColor Yellow
