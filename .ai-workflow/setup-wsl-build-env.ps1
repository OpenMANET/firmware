<#
  OpenMANET Pi5 port - post-reboot WSL build environment bootstrap.

  Everything this script needs is already staged under
  C:\AI-Projects\OpenMANET-Pi5\wsl-stage (WSL runtime MSI already installed,
  Ubuntu 24.04 rootfs downloaded). The Windows optional components
  "VirtualMachinePlatform" and "Microsoft-Windows-Subsystem-Linux" have been
  enabled but require a reboot before WSL2 can start.

  Run this ONCE after the reboot, from an elevated PowerShell:
      powershell -ExecutionPolicy Bypass -File .ai-workflow\setup-wsl-build-env.ps1

  It is idempotent - re-running it is safe.
#>
$ErrorActionPreference = 'Stop'

$Wsl      = 'C:\Program Files\WSL\wsl.exe'
$Stage    = 'C:\AI-Projects\OpenMANET-Pi5\wsl-stage'
$Rootfs   = Join-Path $Stage 'ubuntu-noble-rootfs.tar.gz'
$Distro   = 'openmanet-build'
$VhdDir   = 'C:\AI-Projects\OpenMANET-Pi5\wsl-openmanet'

function Say($m) { Write-Host "[setup-wsl] $m" -ForegroundColor Cyan }

if (-not (Test-Path $Wsl))    { throw "WSL runtime missing at $Wsl" }
if (-not (Test-Path $Rootfs)) { throw "Ubuntu rootfs missing at $Rootfs" }

Say 'Checking WSL2 availability...'
$status = & $Wsl --status 2>&1 | Out-String
if ($status -match 'virtualization is not enabled') {
    throw "WSL2 still cannot start. The reboot has not been performed, or virtualization is disabled in BIOS/UEFI (enable AMD SVM / SVM Mode)."
}
Say 'WSL2 is available.'

# --- Import the build distro ------------------------------------------------
$existing = (& $Wsl --list --quiet) -replace "`0", '' -split "`r?`n" | ForEach-Object { $_.Trim() }
if ($existing -contains $Distro) {
    Say "Distro '$Distro' already exists - skipping import."
} else {
    Say "Importing '$Distro' from $Rootfs into $VhdDir (this takes a minute)..."
    New-Item -ItemType Directory -Force $VhdDir | Out-Null
    & $Wsl --import $Distro $VhdDir $Rootfs --version 2
    if ($LASTEXITCODE -ne 0) { throw "wsl --import failed with $LASTEXITCODE" }
    Say 'Import complete.'
}

# --- Global WSL resource limits --------------------------------------------
# 16C/32T, ~61GB RAM host. Leave headroom for Windows.
$wslconfig = Join-Path $env:USERPROFILE '.wslconfig'
if (-not (Test-Path $wslconfig)) {
    Say "Writing $wslconfig"
    @'
[wsl2]
memory=48GB
processors=24
swap=16GB
localhostForwarding=true
'@ | Set-Content -Encoding utf8 $wslconfig
} else {
    Say "$wslconfig already exists - left untouched."
}

# --- Provision the distro ---------------------------------------------------
$provision = Join-Path $PSScriptRoot 'provision-build-env.sh'
if (-not (Test-Path $provision)) { throw "Missing $provision" }

Say 'Provisioning Ubuntu (packages + build user + repo clone). This takes several minutes...'
# Feed the script over stdin so we do not depend on /mnt/c line endings or exec bits.
Get-Content -Raw $provision | & $Wsl -d $Distro -u root -- bash -s
if ($LASTEXITCODE -ne 0) { throw "Provisioning failed with exit code $LASTEXITCODE" }

Say 'DONE. Build environment ready.'
Say "Enter it with:  wsl -d $Distro -u builder"
Say "Build tree:     ~/openmanet/firmware  (git remote 'winrepo' -> /mnt/c/AI-Projects/OpenMANET-Pi5/firmware)"
