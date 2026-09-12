[CmdletBinding()]
param(
    [string]$Version = "1.0.0",
    [switch]$AllowUnsignedDevelopmentBuild
)
$ErrorActionPreference = "Stop"
if (-not $AllowUnsignedDevelopmentBuild) { throw "Unsigned packages are development-only. Pass -AllowUnsignedDevelopmentBuild only on an owned development laptop." }
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$out = Join-Path $root "dist"
New-Item -ItemType Directory -Force $out | Out-Null
python -m pip install -r (Join-Path $root "requirements.txt")
Push-Location $root
try { python -m PyInstaller --clean --noconfirm --onefile --name OnyxAgent --paths $root onyx_agent_entry.py } finally { Pop-Location }
$wix = Get-Command wix -ErrorAction SilentlyContinue
if (-not $wix) { throw "WiX v4 is required. Install WiX, then rerun this script." }
$agentExe = Resolve-Path (Join-Path $out "OnyxAgent.exe")
& $wix.Source build -arch x64 -d "AgentExe=$agentExe" (Join-Path $PSScriptRoot "OnyxAgent.wxs") -o (Join-Path $out "OnyxAgent-$Version-windows-x64.msi")
if ($LASTEXITCODE -ne 0) { throw "WiX MSI build failed." }
Get-FileHash (Join-Path $out "OnyxAgent-$Version-windows-x64.msi") -Algorithm SHA256 | Format-List | Out-File (Join-Path $out "OnyxAgent-$Version-windows-x64.sha256.txt")
