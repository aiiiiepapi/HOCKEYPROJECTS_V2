# KHL discovery probe ROUND 2 — paste-block PowerShell (2026-08-05)
# Round 1 verified: calendars = schedule authority (scoped counts exact),
# text broadcasts have explicit pulls/returns/penalties/dp + coaches + EN-TOI
# tables, but NO goal times. Round 2 targets: protocol/resume payloads (goal
# times?), English channel, and text-broadcast archive depth on old seasons.
# Run from the repo clone (C:\dev\HOCKEYPROJECTS_V2_scrape):
#   cd C:\dev\HOCKEYPROJECTS_V2_scrape
#   git pull origin claude/khl-scrape-f5emx6
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   & .\tools\probe2_khl.ps1

$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$repo = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repo '.git'))) { Write-Host "FATAL: $repo is not a git repo"; exit 1 }
Set-Location $repo
git pull origin claude/khl-scrape-f5emx6

$out = Join-Path $repo 'tests\reference_raw\khl_probe2'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$manifest = Join-Path $out 'manifest.csv'
'file,url,http_code,bytes,sha256,utc' | Set-Content -Encoding UTF8 $manifest

$H = @{
  'User-Agent'      = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
  'Accept'          = 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8'
  'Accept-Language' = 'ru,en;q=0.8'
}

function Probe([string]$url, [string]$name) {
  Start-Sleep -Milliseconds 700
  $f = Join-Path $out $name
  $code = 'ERR'; $bytes = 0; $sha = ''
  try {
    $r = Invoke-WebRequest -Uri $url -Headers $H -TimeoutSec 60 -MaximumRedirection 5 -OutFile $f -PassThru -UseBasicParsing
    $code = [int]$r.StatusCode
  } catch {
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    else { $code = 'ERR:' + $_.Exception.Message.Split("`n")[0] }
  }
  if (Test-Path $f) { $bytes = (Get-Item $f).Length; $sha = (Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() }
  $utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  ('"{0}","{1}",{2},{3},{4},{5}' -f $name, $url, $code, $bytes, $sha, $utc) | Add-Content -Encoding UTF8 $manifest
  Write-Host ("{0,-40} {1,6}  {2,10} B" -f $name, $code, $bytes)
}

# --- named game: Barys-Lada 2025-26 #604, gid 898094 (text page already in round 1)
Probe 'https://www.khl.ru/game/1369/898094/protocol/'  'proto_1369_898094.html'
Probe 'https://www.khl.ru/game/1369/898094/resume/'    'resume_1369_898094.html'
Probe 'https://en.khl.ru/game/1369/898094/protocol/'   'en_proto_1369_898094.html'
# --- archive depth: FIRST regular-season game of each older season
# 2022-23: tid 1154, ids 881261..882008
Probe 'https://text.khl.ru/text/881261.html'           'text_881261.html'
Probe 'https://www.khl.ru/game/1154/881261/protocol/'  'proto_1154_881261.html'
# mid-season 2022-23 spot (id base + 439)
Probe 'https://text.khl.ru/text/881700.html'           'text_881700.html'
# 2023-24: tid 1217, ids 885442..886223
Probe 'https://text.khl.ru/text/885442.html'           'text_885442.html'
Probe 'https://www.khl.ru/game/1217/885442/protocol/'  'proto_1217_885442.html'
# 2024-25: tid 1288, ids 889850..890631
Probe 'https://text.khl.ru/text/889850.html'           'text_889850.html'
Probe 'https://www.khl.ru/game/1288/889850/protocol/'  'proto_1288_889850.html'

Write-Host "`n=== summary ==="
Import-Csv $manifest | Format-Table file, http_code, bytes -AutoSize

git add tests/reference_raw/khl_probe2 .gitattributes
git commit -m "KHL probe round 2: protocol/resume payloads, EN channel, text-broadcast archive depth (named games all 4 seasons)"
git push -u origin claude/khl-scrape-f5emx6
Write-Host "`nDONE. Tell the KHL session round 2 landed."
