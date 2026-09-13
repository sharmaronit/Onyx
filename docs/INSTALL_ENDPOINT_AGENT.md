# Installing the Onyx Endpoint Agent

The Windows MSI fix is included in the current `main` branch. If GitHub still shows an older tree, refresh the page and select `main` from the branch menu.

Onyx Agent includes a desktop status application and a privileged background service. The service starts in an idle state after installation so the desktop application can enroll the laptop without receiving or reading its device credential.

## Windows 10/11 x64

1. Install the latest MSI as an administrator.
2. Open **Onyx Agent** from the Start menu and enter the HTTPS backend URL and one-use enrollment token in the enrollment screen.
5. Verify with `Get-Service OnyxEndpointAgent`. Its status should be `Running`.

The MSI starts the service during installation. Enrollment sends the one-use token through a local named pipe to that service. The service stores the resulting credential with machine-scope DPAPI; the desktop process never receives it. If the service does not start, inspect the **Onyx Endpoint Agent** source in Event Viewer and `%ProgramData%\Onyx\logs\service-startup.jsonl`.

## macOS (Intel and Apple Silicon)

1. Use a Developer ID-signed and Apple-notarized DMG for distribution to other people.
2. Open the DMG and install its PKG as an administrator.
3. Open **Onyx Agent** from Applications.
4. Enter the HTTPS backend URL and one-use enrollment token in the enrollment screen.
5. Verify with `sudo launchctl print system/com.onyx.endpoint-agent`.

The package starts the LaunchDaemon in an idle state. Enrollment goes through its local Unix socket, and the service stores the device credential in the System Keychain. The app also provides connection retry, status, and sanitized diagnostics export.

## Signing requirements

The GitHub package workflow supports these repository secrets:

- Windows: `ONYX_WINDOWS_CERTIFICATE_PFX_BASE64`, `ONYX_WINDOWS_SIGNING_PASSWORD`
- Apple certificate bundle: `APPLE_CERTIFICATE_P12_BASE64`, `APPLE_CERTIFICATE_PASSWORD`
- Apple identities: `APPLE_APPLICATION_IDENTITY`, `APPLE_INSTALLER_IDENTITY`
- Apple notarization: `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`

Without Windows signing, SmartScreen may warn. Without Apple Developer ID signing and notarization, Gatekeeper may identify the downloaded package as unsafe. Do not distribute unsigned builds to employee laptops.

The macOS release job now fails closed when any Apple credential is absent. It notarizes and staples both the signed installer package and the signed DMG, then runs `codesign`, `pkgutil`, `stapler`, and `spctl` verification before publication. An ad-hoc signed development DMG is not a customer-distribution build and must not be published as one.
