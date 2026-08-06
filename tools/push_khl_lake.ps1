# KHL lake push - paste-block PowerShell (2026-08-05, rev 3).
# ASCII-only; $ErrorActionPreference stays 'Continue' because git writes
# routine progress to stderr (PS 5.1 + 'Stop' turns that into a fatal
# NativeCommandError - the rev-2 failure). Failures are checked explicitly
# via $LASTEXITCODE at every step that matters.
# Publishes C:\dev\khl_lake\khl\<year>\ to V2 orphan branch `khl-data-lake`,
# one commit+push per season. Verbatim-safe: core.autocrlf=false +
# .gitattributes `-text` committed before any payload.
# Run AFTER verify_khl_lake.py reports OVERALL: PASS. Safe to re-run.

$ErrorActionPreference = 'Continue'
$lakeSrc  = 'C:\dev\khl_lake\khl'
$repoUrl  = 'https://github.com/aiiiiepapi/HOCKEYPROJECTS_V2.git'
$lakeRepo = 'C:\dev\khl_lake_repo'
$branch   = 'khl-data-lake'

function Assert-Ok([string]$what) {
  if ($LASTEXITCODE -ne 0) { Write-Host "FATAL at: $what (exit $LASTEXITCODE) - STOP, report to session"; exit 1 }
}

if (-not (Test-Path (Join-Path $lakeSrc 'COMPLETENESS.md'))) {
  Write-Host 'FATAL: run verify_khl_lake.py --write-completeness first (COMPLETENESS.md missing).'
  exit 1
}

if (-not (Test-Path (Join-Path $lakeRepo '.git'))) {
  git init $lakeRepo
  Assert-Ok 'git init'
  Set-Location $lakeRepo
  git remote add origin $repoUrl
} else {
  Set-Location $lakeRepo
}
git config core.autocrlf false

# does the lake branch already exist on the remote?
$remoteRef = git ls-remote --heads origin $branch
Assert-Ok 'git ls-remote'
if ($remoteRef) {
  git fetch origin $branch
  Assert-Ok 'git fetch lake branch'
  git checkout -B $branch FETCH_HEAD
  Assert-Ok 'git checkout existing lake branch'
} else {
  git checkout -B $branch
  Assert-Ok 'git checkout new lake branch'
}

# verbatim protection FIRST, committed before any raw file
if (-not (Test-Path '.gitattributes')) {
  "# Raw lake: no line-ending conversion, ever.`nkhl/** -text`n" |
    Set-Content -NoNewline -Encoding ascii '.gitattributes'
  git add .gitattributes
  git commit -m 'khl-data-lake: .gitattributes -text (verbatim protection before any payload)'
  Assert-Ok 'commit .gitattributes'
  git push -u origin $branch
  Assert-Ok 'push .gitattributes'
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
  Assert-Ok "git add season ${year}"
  git commit -m "KHL lake season ${year}-ending: raw text+protocol per game, calendar authority, manifest (fetched on Seb's PC)"
  Assert-Ok "git commit season ${year}"
  git push -u origin $branch
  Assert-Ok "git push season ${year}"
}

# lake-root completeness file last
if (-not (Test-Path 'khl\COMPLETENESS.md')) {
  Copy-Item (Join-Path $lakeSrc 'COMPLETENESS.md') 'khl\COMPLETENESS.md'
  git add 'khl\COMPLETENESS.md'
  git commit -m 'KHL lake: completeness report (verify_khl_lake.py)'
  Assert-Ok 'commit COMPLETENESS'
  git push -u origin $branch
  Assert-Ok 'push COMPLETENESS'
}
Write-Host ''
Write-Host 'DONE. Tell the KHL session the lake is pushed.'
