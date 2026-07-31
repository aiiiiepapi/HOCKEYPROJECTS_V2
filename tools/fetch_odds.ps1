# Daily NHL moneyline snapshot (The Odds API free tier, ~1 credit/run).
# Runs on Seb's PC (cloud proxy blocks direct API calls). Saves into the
# v2 repo; push with the nightly job. Usage: powershell -File fetch_odds.ps1
$key = Get-Content (Join-Path $PSScriptRoot "..\config\odds_api_key.txt")
$url = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey=$key&regions=us&markets=h2h&oddsFormat=american"
$out = Join-Path $PSScriptRoot ("..\data\odds\odds_" + (Get-Date -Format "yyyyMMdd") + ".json")
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
Invoke-RestMethod -Uri $url | ConvertTo-Json -Depth 10 | Set-Content $out -Encoding UTF8
Copy-Item $out (Join-Path $PSScriptRoot "..\data\odds\odds_latest.json") -Force
Write-Host "saved $out"
