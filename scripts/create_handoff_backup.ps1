$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backupsDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupsDir | Out-Null

$shortHash = (git -C $root rev-parse --short HEAD).Trim()
$fullHash = (git -C $root rev-parse HEAD).Trim()
$zipPath = Join-Path $backupsDir ("overlap-aware-speaker-asr_handoff_{0}.zip" -f $shortHash)

$stagingRoot = Join-Path $backupsDir ("_staging_{0}" -f $shortHash)
$repoStaging = Join-Path $stagingRoot "overlap-aware-speaker-asr"

if (Test-Path $stagingRoot) {
    Remove-Item -Recurse -Force $stagingRoot
}
New-Item -ItemType Directory -Force -Path $repoStaging | Out-Null

$excludeNames = @(".git", ".venv", "chat_upload", "backups", "__pycache__")

Get-ChildItem -Path $root -Force | ForEach-Object {
    $name = $_.Name
    if ($excludeNames -notcontains $name) {
        $destination = Join-Path $repoStaging $name
        if ($_.PSIsContainer) {
            Copy-Item -Recurse -Force -Path $_.FullName -Destination $destination
        } else {
            Copy-Item -Force -Path $_.FullName -Destination $destination
        }
    }
}

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path (Join-Path $repoStaging "*") -DestinationPath $zipPath -CompressionLevel Optimal

Remove-Item -Recurse -Force $stagingRoot

Write-Host "current commit hash: $fullHash"
Write-Host "zip path: $zipPath"
Write-Host "next suggested git tag command:"
Write-Host 'git tag -a wufangzhou-core-complete -m "Core technical pipeline completed by WUFANGZHOU"'
