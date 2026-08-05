# SHL probe 1 — discovery fetch pack (run on Seb's PC, paste-block)
# Saves raw samples to Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\shl_probe1\
# and prints a summary block to paste back to the scrape session.
# Fetch-only. No auth. Polite delays. Nothing is edited after saving.

$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$out = "$env:USERPROFILE\Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\shl_probe1"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
$script:LOG = New-Object System.Collections.ArrayList

function Fetch([string]$name, [string]$url) {
    Start-Sleep -Milliseconds 700
    $path = Join-Path $out $name
    try {
        Invoke-WebRequest -Uri $url -UserAgent $UA -UseBasicParsing -TimeoutSec 30 -OutFile $path | Out-Null
        $bytes = (Get-Item $path).Length
        [void]$script:LOG.Add(("OK   {0}  {1} B  {2}" -f $name, $bytes, $url))
        return (Get-Content -Raw -Encoding UTF8 $path)
    } catch {
        $code = ''
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        [void]$script:LOG.Add(("FAIL {0}  [{1}]  {2}  :: {3}" -f $name, $code, $url, $_.Exception.Message))
        return $null
    }
}

function ExtractApiPaths([string]$html) {
    if (-not $html) { return @() }
    $m = [regex]::Matches($html, '(?<![A-Za-z0-9])/api/[A-Za-z0-9\-_/\.]+')
    return @($m | ForEach-Object { $_.Value } | Sort-Object -Unique)
}

# ---------- A. shl.se ----------
$schedUrl = 'https://www.shl.se/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B&completeSeason=all&homeAway=all&allGames=all'
$shlHtml = Fetch 'shl_schedule.html' $schedUrl

$apiPaths = @(ExtractApiPaths $shlHtml)
$uuids = @()
$gameLinks = @()
if ($shlHtml) {
    $uuids = @([regex]::Matches($shlHtml, '"(seasonUuid|seriesUuid|gameTypeUuid|ssgtUuid)"\s*:\s*"([^"]+)"') |
        ForEach-Object { $_.Groups[1].Value + '=' + $_.Groups[2].Value } | Sort-Object -Unique)
    $gameLinks = @([regex]::Matches($shlHtml, 'href="(/[^"]*game[^"]*)"') |
        ForEach-Object { $_.Groups[1].Value } |
        Where-Object { $_ -notmatch 'game-schedule|game-stats' } | Sort-Object -Unique)
}

# Auto-fetch the api paths the page itself references (capped at 12)
$i = 0
foreach ($p in ($apiPaths | Select-Object -First 12)) {
    $i++
    $fn = 'shl_api_{0:D2}{1}.txt' -f $i, ($p -replace '[^A-Za-z0-9]', '_')
    if ($fn.Length -gt 80) { $fn = $fn.Substring(0, 76) + '.txt' }
    Fetch $fn ('https://www.shl.se' + $p) | Out-Null
}

# Known-shape schedule endpoint guesses (only 3, in case the HTML hides them)
Fetch 'shl_guess_sportsv2_schedule.json' 'https://www.shl.se/api/sports-v2/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B' | Out-Null
Fetch 'shl_guess_seasons.json' 'https://www.shl.se/api/sports-v2/seasons' | Out-Null
Fetch 'shl_guess_site-settings.json' 'https://www.shl.se/api/site-settings' | Out-Null

# First game page, if any link was found — to expose gameday/pbp endpoints
if ($gameLinks.Count -gt 0) {
    $g = $gameLinks[0]
    $gHtml = Fetch 'shl_gamepage.html' ('https://www.shl.se' + $g)
    $j = 0
    foreach ($p in (@(ExtractApiPaths $gHtml) | Select-Object -First 12)) {
        $j++
        $fn = 'shl_gameapi_{0:D2}{1}.txt' -f $j, ($p -replace '[^A-Za-z0-9]', '_')
        if ($fn.Length -gt 80) { $fn = $fn.Substring(0, 76) + '.txt' }
        Fetch $fn ('https://www.shl.se' + $p) | Out-Null
    }
}

# ---------- B. official SHL open API ----------
Fetch 'shl_openapi_root.txt' 'https://api.shl.se/' | Out-Null
Fetch 'shl_openapi_doc.html' 'http://doc.openapi.shl.se/' | Out-Null

# ---------- C. stats.swehockey.se (federation) ----------
$sweRoot = Fetch 'swe_root.html' 'https://stats.swehockey.se/'
$sweSched = Fetch 'swe_sched_18263.html' 'https://stats.swehockey.se/ScheduleAndResults/Schedule/18263'
Fetch 'swe_hist_root.html' 'https://historical.stats.swehockey.se/' | Out-Null

$seasonOptions = @()
$gameIds = @()
if ($sweSched) {
    $seasonOptions = @([regex]::Matches($sweSched, '<option[^>]*value="(\d+)"[^>]*>\s*([^<]+?)\s*</option>') |
        ForEach-Object { $_.Groups[1].Value + ' = ' + $_.Groups[2].Value } | Select-Object -First 60)
    $gameIds = @([regex]::Matches($sweSched, '/Game/Events/(\d+)') |
        ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
}
if ($gameIds.Count -gt 0) {
    $gid = $gameIds[0]
    Fetch ('swe_events_' + $gid + '.html') ('https://stats.swehockey.se/Game/Events/' + $gid) | Out-Null
    Fetch ('swe_lineups_' + $gid + '.html') ('https://stats.swehockey.se/Game/LineUps/' + $gid) | Out-Null
}

$dns = ''
try { $dns = (Resolve-DnsName 'statistik.swehockey.se' -ErrorAction Stop | Select-Object -First 1).IPAddress } catch { $dns = 'NXDOMAIN / ' + $_.Exception.Message }

# ---------- Summary ----------
Write-Host ''
Write-Host '===== SHL PROBE 1 SUMMARY (paste everything below back) ====='
Write-Host ("probe_dir: " + $out)
Write-Host '--- fetch log ---'
$script:LOG | ForEach-Object { Write-Host $_ }
Write-Host '--- shl.se: distinct /api/ paths in schedule page ---'
$apiPaths | Select-Object -First 30 | ForEach-Object { Write-Host $_ }
Write-Host '--- shl.se: uuids seen ---'
$uuids | Select-Object -First 30 | ForEach-Object { Write-Host $_ }
Write-Host '--- shl.se: candidate game links ---'
$gameLinks | Select-Object -First 10 | ForEach-Object { Write-Host $_ }
Write-Host '--- swehockey: season dropdown options (id = label) ---'
$seasonOptions | ForEach-Object { Write-Host $_ }
Write-Host ("--- swehockey: game ids on schedule 18263: {0} found, first {1} ---" -f $gameIds.Count, ($gameIds | Select-Object -First 1))
Write-Host ("--- DNS statistik.swehockey.se: " + $dns)
Write-Host '===== END SHL PROBE 1 SUMMARY ====='
