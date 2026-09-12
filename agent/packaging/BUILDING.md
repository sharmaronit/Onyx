# Packaging

Build the executable with `pyinstaller --onefile --name OnyxAgent -m onyx_agent`. Windows CI builds `OnyxAgent-<version>-windows-x64.msi` using WiX; macOS CI copies the universal executable and uses `pkgbuild` then `productbuild` for `OnyxAgent-<version>-macos-universal.pkg`.

Installer scripts must create the restricted data directory, preserve credential/queue during upgrades, and remove service/LaunchDaemon, credentials, queue, logs, and application files on uninstall. Builds are development-only until Windows signing and Apple Developer ID signing/notarization are configured.
