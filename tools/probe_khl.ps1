# KHL discovery probe — paste-block PowerShell (khl-scrape session, 2026-08-05)
# Purpose: FIRST real data contact with KHL sources, run on Seb's PC
# (residential connection). Fetch-only. Saves every response VERBATIM to
# tests/reference_raw/khl_probe/ on branch claude/khl-scrape-f5emx6 and
# pushes, so the cloud session can analyze raw payloads.
# Safe to re-run: existing files are overwritten, nothing else is touched.

$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

# --- repo setup -------------------------------------------------------------
$repo = 'C:\dev\HOCKEYPROJECTS_V2'
if (-not (Test-Path $repo)) {
  git clone https://github.com/aiiiiepapi/HOCKEYPROJECTS_V2.git $repo
}
Set-Location $repo
git fetch origin
git checkout claude/khl-scrape-f5emx6 2>$null
if ($LASTEXITCODE -ne 0) { git checkout -b claude/khl-scrape-f5emx6 origin/claude/khl-scrape-f5emx6 }
git pull origin claude/khl-scrape-f5emx6

$out = Join-Path $repo 'tests\reference_raw\khl_probe'
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
    $r = Invoke-WebRequest -Uri $url -Headers $H -TimeoutSec 40 -MaximumRedirection 5 -OutFile $f -PassThru -UseBasicParsing
    $code = [int]$r.StatusCode
  } catch {
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    else { $code = 'ERR:' + $_.Exception.Message.Split("`n")[0] }
  }
  if (Test-Path $f) {
    $bytes = (Get-Item $f).Length
    $sha = (Get-FileHash -Algorithm SHA256 $f).Hash.ToLower()
  }
  $utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  ('"{0}","{1}",{2},{3},{4},{5}' -f $name, $url, $code, $bytes, $sha, $utc) | Add-Content -Encoding UTF8 $manifest
  Write-Host ("{0,-44} {1,6}  {2,10} B  {3}" -f $name, $code, $bytes, $url)
  return $code
}

Write-Host "`n=== STAGE A: reachability ==="
Probe 'https://www.khl.ru/'                    'A_khl_root.html'        | Out-Null
Probe 'https://en.khl.ru/'                     'A_en_root.html'         | Out-Null
Probe 'https://text.khl.ru/'                   'A_text_root.html'       | Out-Null
Probe 'https://online.khl.ru/online/'          'A_online_root.html'     | Out-Null
Probe 'https://api.khl.ru/'                    'A_api_khl.html'         | Out-Null
Probe 'https://khl.api.webcaster.pro/'         'A_webcaster_root.html'  | Out-Null
Probe 'https://www.khl.ru/robots.txt'          'A_robots.txt'           | Out-Null
Probe 'https://www.khl.ru/sitemap.xml'         'A_sitemap.xml'          | Out-Null

Write-Host "`n=== STAGE B: named samples ==="
# Calendars: all four target seasons (1154=22-23, 1217=23-24, 1288=24-25, 1369=25-26)
Probe 'https://www.khl.ru/calendar/1369/00/'   'B_calendar_1369.html'   | Out-Null
Probe 'https://www.khl.ru/calendar/1288/00/'   'B_calendar_1288.html'   | Out-Null
Probe 'https://www.khl.ru/calendar/1217/00/'   'B_calendar_1217.html'   | Out-Null
Probe 'https://www.khl.ru/calendar/1154/00/'   'B_calendar_1154.html'   | Out-Null
# Known text broadcast (Barys-Lada, 2025-26 game 604)
Probe 'https://text.khl.ru/text/898094.html'   'B_text_898094.html'     | Out-Null
# Hardcoded game-page guess from the same id (platform-global id hypothesis)
Probe 'https://www.khl.ru/game/1369/898094/'   'B_game_1369_898094.html' | Out-Null
# Mobile-API candidates (memory-grade guesses — verify, never assume)
Probe 'https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json'                            'B_events_v2.json'        | Out-Null
Probe 'https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json?q[tournament_id_eq]=1369'   'B_events_v2_t1369.json'  | Out-Null
Probe 'https://api.khl.ru/khl_mobile/events_v2.json'                                           'B_events_v2_apihost.json' | Out-Null

Write-Host "`n=== STAGE C: game pages extracted from calendar/text payloads ==="
$gameIds = @()
foreach ($cal in @('B_calendar_1369.html','A_text_root.html','A_khl_root.html')) {
  $p = Join-Path $out $cal
  if (Test-Path $p) {
    $raw = Get-Content -Raw -Encoding UTF8 $p
    foreach ($m in [regex]::Matches($raw, '/game/(\d+)/(\d+)')) {
      $gameIds += ,@($m.Groups[1].Value, $m.Groups[2].Value)
    }
    foreach ($m in [regex]::Matches($raw, 'text\.khl\.ru/text/(\d+)\.html')) {
      $gameIds += ,@('', $m.Groups[1].Value)
    }
  }
}
$seen = @{}; $picked = @()
foreach ($g in $gameIds) { if (-not $seen.ContainsKey($g[1])) { $seen[$g[1]] = 1; $picked += ,$g } }
$picked = $picked | Select-Object -First 3
if ($picked.Count -eq 0) { Write-Host 'No game links found in raw payloads (JS-rendered pages?) — cloud session will mine XHR URLs from the saved HTML.' }
foreach ($g in $picked) {
  $tid = $g[0]; $gid = $g[1]
  if ($tid -eq '') { $tid = '1369' }
  Probe ("https://www.khl.ru/game/{0}/{1}/" -f $tid, $gid)            ("C_game_{0}_{1}.html"   -f $tid, $gid) | Out-Null
  Probe ("https://www.khl.ru/game/{0}/{1}/protocol/" -f $tid, $gid)   ("C_proto_{0}_{1}.html"  -f $tid, $gid) | Out-Null
  Probe ("https://www.khl.ru/game/{0}/{1}/online/" -f $tid, $gid)     ("C_online_{0}_{1}.html" -f $tid, $gid) | Out-Null
  Probe ("https://text.khl.ru/text/{0}.html" -f $gid)                 ("C_text_{0}.html"       -f $gid)       | Out-Null
  Probe ("https://en.khl.ru/game/{0}/{1}/" -f $tid, $gid)             ("C_engame_{0}_{1}.html" -f $tid, $gid) | Out-Null
}

Write-Host "`n=== summary ==="
Import-Csv $manifest | Format-Table file, http_code, bytes -AutoSize

git add tests/reference_raw/khl_probe
git commit -m "KHL probe: raw discovery samples from PC (reachability + calendars + game pages + mobile-API candidates)"
git push -u origin claude/khl-scrape-f5emx6
Write-Host "`nDONE. If push succeeded, tell the KHL session the probe landed."
