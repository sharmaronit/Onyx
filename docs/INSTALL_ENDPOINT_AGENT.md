# Installing the Onyx Endpoint Agent

Onyx Agent is a background service. It does not open a desktop window after installation. Installation copies and registers the service; secure enrollment starts it.

## Windows 10/11 x64

1. Install the latest MSI as an administrator.
2. Open PowerShell with **Run as administrator**.
3. Run `& "C:\Program Files\Onyx\OnyxAgent.exe" enroll`.
4. Enter the HTTPS backend URL and one-use enrollment token when prompted.
5. Verify with `Get-Service OnyxEndpointAgent`. Its status should be `Running`.

The installer does not start an unenrolled service. Enrollment checks elevation before consuming the token, stores the device credential with machine-scope DPAPI, and starts the registered service.

## macOS (Intel and Apple Silicon)

1. Use a Developer ID-signed and Apple-notarized DMG for distribution to other people.
2. Open the DMG and install its PKG as an administrator.
3. Run `sudo onyx-agent enroll` in Terminal.
4. Enter the HTTPS backend URL and one-use enrollment token when prompted.
5. Verify with `sudo launchctl print system/com.onyx.endpoint-agent`.

The package installs the LaunchDaemon definition without starting an unenrolled daemon. Enrollment stores the device credential in the System Keychain, loads the LaunchDaemon, and starts it.

## Signing requirements

The GitHub package workflow supports these repository secrets:

- Windows: `ONYX_WINDOWS_CERTIFICATE_PFX_BASE64`, `ONYX_WINDOWS_SIGNING_PASSWORD`
- Apple certificate bundle: `APPLE_CERTIFICATE_P12_BASE64`, `APPLE_CERTIFICATE_PASSWORD`
- Apple identities: `APPLE_APPLICATION_IDENTITY`, `APPLE_INSTALLER_IDENTITY`
- Apple notarization: `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`

Without Windows signing, SmartScreen may warn. Without Apple Developer ID signing and notarization, Gatekeeper may identify the downloaded package as unsafe. Do not distribute unsigned builds to employee laptops.
