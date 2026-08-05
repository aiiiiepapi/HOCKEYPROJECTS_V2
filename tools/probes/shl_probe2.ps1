# SHL probe 2 — historical season verification + shl.se endpoint discovery
# (run on Seb's PC, paste-block). Auto-pushes results via C:\dev\HP_V2.
# Fetch-only, no auth, polite delays, raw responses saved verbatim.

$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$out = "$env:USERPROFILE\Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\shl_probe2"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
$script:LOG = New-Object System.Collections.ArrayList

function Fetch([string]$name, [string]$url) {
    Start-Sleep -Milliseconds 700
    $path = Join-Path $out $name
    try {
        Invoke-WebRequest -Uri $url -UserAgent $UA -UseBasicParsing -TimeoutSec 60 -OutFile $path | Out-Null
        $bytes = (Get-Item $path).Length
        [void]$script:LOG.Add(("OK   {0}  {1} B  {2}" -f $name, $bytes, $url))
        return (Get-Content -Raw -Encoding UTF8 $path)
    } catch {
        $code = ''
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        [void]$script:LOG.Add(("FAIL {0}  [{1}]  {2}" -f $name, $code, $url))
        return $null
    }
}

# ---------- A. swehockey: verify historical SHL season series ids ----------
# Dropdown on 18263 says: 2022-23=14296, 2023-24=15791, 2024-25=17556.
# Google titles disagreed (said "Play Out SHL") -> verify from content, trust neither.
$seasonCheck = New-Object System.Collections.ArrayList
foreach ($sid in @(14296, 15791, 17556)) {
    $html = Fetch ("swe_sched_" + $sid + ".html") ("https://stats.swehockey.se/ScheduleAndResults/Schedule/" + $sid)
    if ($html) {
        $title = ([regex]::Match($html, '<title>\s*(.*?)\s*</title>', 'Singleline')).Groups[1].Value -replace '\s+', ' '
        $label = ([regex]::Match($html, '<label>\s*([0-9]{4}-[0-9]{2})\s*-\s*([^<]+?)\s*</label>')).Value -replace '<[^>]+>', '' -replace '\s+', ' '
        $ids = @([regex]::Matches($html, '/Game/Events/(\d+)') | ForEach-Object { [int]$_.Groups[1].Value } | Sort-Object -Unique)
        $dates = @([regex]::Matches($html, '\b(20\d\d-\d\d-\d\d)\b') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
        $line = "sid=$sid title='$title' label='$label' games=$($ids.Count) idrange=$($ids[0])-$($ids[-1]) daterange=$($dates[0])..$($dates[-1])"
        [void]$seasonCheck.Add($line)
        # one Events + (first season only) one LineUps spot-check per historical season
        if ($ids.Count -gt 0) {
            Fetch ("swe_events_" + $ids[0] + ".html") ("https://stats.swehockey.se/Game/Events/" + $ids[0]) | Out-Null
            if ($sid -eq 14296) {
                Fetch ("swe_lineups_" + $ids[0] + ".html") ("https://stats.swehockey.se/Game/LineUps/" + $ids[0]) | Out-Null
            }
        }
    }
}

# OT game 2025-26 (Farjestad-Rogle 2-3 OT, 2025-09-13) + Reports artifact check
Fetch 'swe_events_1004311.html' 'https://stats.swehockey.se/Game/Events/1004311' | Out-Null
Fetch 'swe_reports_1004308.html' 'https://stats.swehockey.se/Game/Reports/1004308' | Out-Null

# ---------- B. shl.se: JS bundle (all API routes) + game endpoint candidates ----------
$bundle = Fetch 'shl_bundle.js' 'https://www.shl.se/assets/index-RNjyxFdd.js'
$apiPaths = @()
$seasonCtx = @()
if ($bundle) {
    $apiPaths = @([regex]::Matches($bundle, '(?<![A-Za-z0-9])/api/[A-Za-z0-9\-_/\.\$\{\}:]+') |
        ForEach-Object { $_.Value } | Sort-Object -Unique)
    $seasonCtx = @([regex]::Matches($bundle, '.{60}seasonUuid.{60}') |
        Select-Object -First 15 | ForEach-Object { $_.Value -replace '\s+', ' ' })
}

$GU = 'bdhvuc5tex'   # FHC-LHC 2025-09-13, from the fetched schedule JSON
$candidates = @(
    "/api/gameday/gameheader/$GU", "/api/gameday/game-header/$GU", "/api/gameday/$GU",
    "/api/gameday/play-by-play/$GU", "/api/gameday/pbp/$GU", "/api/gameday/boxscore/$GU",
    "/api/gameday/lineup/$GU", "/api/gameday/lineups/$GU",
    "/api/sports-v2/game/$GU", "/api/sports-v2/game-info/$GU",
    "/api/sports-v2/season-series-game-types", "/api/sports-v2/series"
)
$k = 0
foreach ($p in $candidates) {
    $k++
    $fn = 'shl_cand_{0:D2}{1}.txt' -f $k, ($p -replace '[^A-Za-z0-9]', '_')
    if ($fn.Length -gt 90) { $fn = $fn.Substring(0, 86) + '.txt' }
    Fetch $fn ('https://www.shl.se' + $p) | Out-Null
}
# game PAGE candidates; extract this page's /api/ refs too
foreach ($gp in @("/game/$GU", "/gamecenter/$GU")) {
    $gHtml = Fetch ('shl_gamepage' + ($gp -replace '[^A-Za-z0-9]', '_') + '.html') ('https://www.shl.se' + $gp)
    if ($gHtml) {
        @([regex]::Matches($gHtml, '(?<![A-Za-z0-9])/api/[A-Za-z0-9\-_/\.]+') | ForEach-Object { $_.Value } |
            Sort-Object -Unique | Select-Object -First 10) | ForEach-Object {
            $k++
            $fn = 'shl_gapi_{0:D2}{1}.txt' -f $k, ($_ -replace '[^A-Za-z0-9]', '_')
            if ($fn.Length -gt 90) { $fn = $fn.Substring(0, 86) + '.txt' }
            Fetch $fn ('https://www.shl.se' + $_) | Out-Null
        }
    }
}

# ---------- C. summary ----------
Write-Host ''
Write-Host '===== SHL PROBE 2 SUMMARY (paste everything below back) ====='
Write-Host '--- fetch log ---'
$script:LOG | ForEach-Object { Write-Host $_ }
Write-Host '--- season id verification (content-derived, trust no dropdown/google) ---'
$seasonCheck | ForEach-Object { Write-Host $_ }
Write-Host ("--- shl bundle: {0} distinct /api/ paths ---" -f $apiPaths.Count)
$apiPaths | Select-Object -First 80 | ForEach-Object { Write-Host $_ }
Write-Host '--- shl bundle: seasonUuid contexts ---'
$seasonCtx | ForEach-Object { Write-Host $_ }
Write-Host '===== END SHL PROBE 2 SUMMARY ====='

# ---------- D. auto-relay to the session branch via C:\dev\HP_V2 ----------
$repo = 'C:\dev\HP_V2'
if (Test-Path (Join-Path $repo '.git')) {
    New-Item -ItemType Directory -Force -Path "$repo\data_samples\shl_probe1" | Out-Null
    New-Item -ItemType Directory -Force -Path "$repo\data_samples\shl_probe2" | Out-Null
    Copy-Item "$env:USERPROFILE\Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\shl_probe1\*" "$repo\data_samples\shl_probe1\" -Force
    Copy-Item "$out\*" "$repo\data_samples\shl_probe2\" -Force
    git -C $repo pull origin claude/shl-scrape-ly11nk
    git -C $repo add data_samples
    git -C $repo commit -m "SHL probe 1+2 raw samples (PC relay)"
    git -C $repo push origin claude/shl-scrape-ly11nk
    Write-Host 'RELAY: pushed data_samples to claude/shl-scrape-ly11nk'
} else {
    Write-Host 'RELAY SKIPPED: C:\dev\HP_V2 is not a git repo — tell the session'
}
