# KHL lake push - paste-block PowerShell (2026-08-05, ASCII-only for
# Windows PowerShell 5.1 ANSI parsing; ${} for variable-colon strings).
# Publishes C:\dev\khl_lake\khl\<year>\ to the V2 repo orphan branch
# `khl-data-lake`, ONE COMMIT + PUSH PER SEASON. Verbatim-safe:
# core.autocrlf=false + .gitattributes `-text` BEFORE any add.
# Run AFTER verify_khl_lake.py reports OVERALL: PASS.
# Safe to re-run: existing branch reused, committed seasons skipped.

$ErrorActionPreference = 'Stop'
$lakeSrc  = 'C:\dev\khl_lake\khl'
$repoUrl  = 'https://github.com/aiiiiepapi/HOCKEYPROJECTS_V2.git'
$lakeRepo = 'C:\dev\khl_lake_repo'
$branch   = 'khl-data-lake'

if (-not (Test-Path (Join-Path $lakeSrc 'COMPLETENESS.md'))) {
  Write-Host 'FATAL: run verify_khl_lake.py --write-completeness first (COMPLETENESS.md missing).'
  exit 1
}

if (-not (Test-Path (Join-Path $lakeRepo '.git'))) {
  git init $lakeRepo
  Set-Location $lakeRepo
  git remote add origin $repoUrl
  git config core.autocrlf false
  git fetch origin ${branch} 2>$null
  if ($LASTEXITCODE -eq 0) {
    git checkout -b $branch "origin/$branch"
  } else {
    git checkout -b $branch
  }
} else {
  Set-Location $lakeRepo
  git config core.autocrlf false
  git fetch origin ${branch} 2>$null
  git checkout $branch
}

# verbatim protection FIRST, committed before any raw file
if (-not (Test-Path '.gitattributes')) {
  "# Raw lake: no line-ending conversion, ever.`nkhl/** -text`n" |
    Set-Content -NoNewline -Encoding ascii '.gitattributes'
  git add .gitattributes
  git commit -m 'khl-data-lake: .gitattributes -text (verbatim protection before any payload)'
  git push -u origin $branch
}

New-Item -ItemType Directory -Force -Path 'khl' | Out-Null
foreach ($year in 2023, 2024, 2025, 2026) {
  $src = Join-Path $lakeSrc "$year"
  $dst = "khl\$year"
  if (-not (Test-Path $src)) { Write-Host "skip $year (not fetched)"; continue }
  if (Test-Path $dst) { Write-Host "skip $year (already in branch)"; continue }
  Write-Host "== season ${year}: copying + committing (about 1 GB, be patient)"
  Copy-Item -Recurse $src $dst
  git add $dst
  git commit -m "KHL lake season ${year}-ending: raw text+protocol per game, calendar authority, manifest (fetched on Seb's PC)"
  git push -u origin $branch
  if ($LASTEXITCODE -ne 0) { Write-Host "PUSH FAILED for ${year} - STOP, report to session"; exit 1 }
}

# lake-root completeness file last
if (-not (Test-Path 'khl\COMPLETENESS.md')) {
  Copy-Item (Join-Path $lakeSrc 'COMPLETENESS.md') 'khl\COMPLETENESS.md'
  git add 'khl\COMPLETENESS.md'
  git commit -m 'KHL lake: completeness report (verify_khl_lake.py)'
  git push -u origin $branch
}
Write-Host ''
Write-Host 'DONE. Tell the KHL session the lake is pushed.'
