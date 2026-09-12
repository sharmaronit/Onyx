#!/bin/bash
set -euo pipefail
VERSION="${1:-1.0.2}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; OUT="$ROOT/dist"; STAGE="$ROOT/build/macos-root"
ARM="$ROOT/packaging/macos/artifacts/OnyxAgent-arm64"; X64="$ROOT/packaging/macos/artifacts/OnyxAgent-x64"
test -f "$ARM" && test -f "$X64" || { echo "Both Intel and Apple Silicon binaries are required." >&2; exit 2; }
SIGNED=0
if [[ -n "${APPLE_APPLICATION_IDENTITY:-}" && -n "${APPLE_INSTALLER_IDENTITY:-}" ]]; then
  codesign --force --options runtime --timestamp --sign "$APPLE_APPLICATION_IDENTITY" "$ARM"
  codesign --force --options runtime --timestamp --sign "$APPLE_APPLICATION_IDENTITY" "$X64"
  SIGNED=1
fi
rm -rf "$STAGE"; mkdir -p "$STAGE/Library/Application Support/Onyx/bin" "$STAGE/Library/LaunchDaemons" "$OUT"
cp "$ARM" "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-arm64"
cp "$X64" "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-x64"
chmod 755 "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-"*
cp "$ROOT/packaging/macos/com.onyx.endpoint-agent.plist" "$STAGE/Library/LaunchDaemons/"
COMPONENT_PKG="$OUT/OnyxAgent-$VERSION-component.pkg"
FINAL_PKG="$OUT/OnyxAgent-$VERSION-macos-universal.pkg"
pkgbuild --root "$STAGE" --scripts "$ROOT/packaging/macos/scripts" --identifier com.onyx.endpoint-agent --version "$VERSION" --install-location / "$COMPONENT_PKG"
if [[ "$SIGNED" = "1" ]]; then
  productbuild --package "$COMPONENT_PKG" --sign "$APPLE_INSTALLER_IDENTITY" "$FINAL_PKG"
else
  mv "$COMPONENT_PKG" "$FINAL_PKG"
fi
hdiutil create -volname "Onyx Agent" -srcfolder "$OUT/OnyxAgent-$VERSION-macos-universal.pkg" -ov -format UDZO "$OUT/OnyxAgent-$VERSION-macos-universal.dmg"
if [[ "$SIGNED" = "1" ]]; then
  codesign --force --timestamp --sign "$APPLE_APPLICATION_IDENTITY" "$OUT/OnyxAgent-$VERSION-macos-universal.dmg"
  : "${APPLE_ID:?APPLE_ID is required for notarization}"
  : "${APPLE_TEAM_ID:?APPLE_TEAM_ID is required for notarization}"
  : "${APPLE_APP_PASSWORD:?APPLE_APP_PASSWORD is required for notarization}"
  xcrun notarytool submit "$OUT/OnyxAgent-$VERSION-macos-universal.dmg" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_PASSWORD" --wait
  xcrun stapler staple "$OUT/OnyxAgent-$VERSION-macos-universal.dmg"
  xcrun stapler validate "$OUT/OnyxAgent-$VERSION-macos-universal.dmg"
fi
shasum -a 256 "$OUT/OnyxAgent-$VERSION-macos-universal.pkg" "$OUT/OnyxAgent-$VERSION-macos-universal.dmg" > "$OUT/OnyxAgent-$VERSION-macos-universal.sha256.txt"
