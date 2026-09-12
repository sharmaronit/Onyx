[CmdletBinding()]
param(
    [string]$Version = "1.0.2",
    [switch]$AllowUnsignedDevelopmentBuild
)
$ErrorActionPreference = "Stop"
if (-not $AllowUnsignedDevelopmentBuild) { throw "Unsigned packages are development-only. Pass -AllowUnsignedDevelopmentBuild only on an owned development laptop." }
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$out = Join-Path $root "dist"
New-Item -ItemType Directory -Force $out | Out-Null
python -m pip install -r (Join-Path $root "requirements.txt")
Push-Location $root
try {
    python -m PyInstaller --clean --noconfirm --onefile --name OnyxAgent --paths $root `
        --hidden-import servicemanager --hidden-import win32timezone `
        --hidden-import win32service --hidden-import win32serviceutil --hidden-import win32event `
        onyx_agent_entry.py
} finally { Pop-Location }
$wix = Get-Command wix -ErrorAction SilentlyContinue
if (-not $wix) { throw "WiX v4 is required. Install WiX, then rerun this script." }
$agentExe = Resolve-Path (Join-Path $out "OnyxAgent.exe")
$signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($env:ONYX_WINDOWS_SIGNING_PFX) {
    if (-not $signTool) { throw "signtool.exe is required when ONYX_WINDOWS_SIGNING_PFX is configured." }
    & $signTool.Source sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f $env:ONYX_WINDOWS_SIGNING_PFX /p $env:ONYX_WINDOWS_SIGNING_PASSWORD $agentExe
    if ($LASTEXITCODE -ne 0) { throw "Signing OnyxAgent.exe failed." }
}
& $wix.Source build -arch x64 -d "AgentExe=$agentExe" -d "ProductVersion=$Version" (Join-Path $PSScriptRoot "OnyxAgent.wxs") -o (Join-Path $out "OnyxAgent-$Version-windows-x64.msi")
if ($LASTEXITCODE -ne 0) { throw "WiX MSI build failed." }
$msiPath = Join-Path $out "OnyxAgent-$Version-windows-x64.msi"
if ($env:ONYX_WINDOWS_SIGNING_PFX) {
    & $signTool.Source sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f $env:ONYX_WINDOWS_SIGNING_PFX /p $env:ONYX_WINDOWS_SIGNING_PASSWORD $msiPath
    if ($LASTEXITCODE -ne 0) { throw "Signing the MSI failed." }
    & $signTool.Source verify /pa /v $msiPath
    if ($LASTEXITCODE -ne 0) { throw "MSI signature verification failed." }
}
Get-FileHash (Join-Path $out "OnyxAgent-$Version-windows-x64.msi") -Algorithm SHA256 | Format-List | Out-File (Join-Path $out "OnyxAgent-$Version-windows-x64.sha256.txt")
