# Kill processes that have "pnpm" or "uvi" in the command line, but not inside node_modules
Get-Process | Where-Object {
    $_.Path -notlike "*node_modules*" -and 
    ($_.Name -match "pnpm|uvi" -or $_.Path -match "pnpm|uvi")
} | ForEach-Object {
    Write-Host "Killing PID $($_.Id) - $($_.Name)"
    Stop-Process -Id $_.Id -Force
}
