#!/bin/bash
set -euo pipefail
VERSION="${1:-1.0.0}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; OUT="$ROOT/dist"; STAGE="$ROOT/build/macos-root"
ARM="$ROOT/packaging/macos/artifacts/OnyxAgent-arm64"; X64="$ROOT/packaging/macos/artifacts/OnyxAgent-x64"
test -f "$ARM" && test -f "$X64" || { echo "Both Intel and Apple Silicon binaries are required." >&2; exit 2; }
rm -rf "$STAGE"; mkdir -p "$STAGE/Library/Application Support/Onyx/bin" "$STAGE/Library/LaunchDaemons" "$OUT"
cp "$ARM" "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-arm64"
cp "$X64" "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-x64"
chmod 755 "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-"*
cp "$ROOT/packaging/macos/com.onyx.endpoint-agent.plist" "$STAGE/Library/LaunchDaemons/"
pkgbuild --root "$STAGE" --scripts "$ROOT/packaging/macos/scripts" --identifier com.onyx.endpoint-agent --version "$VERSION" --install-location / "$OUT/OnyxAgent-$VERSION-macos-universal.pkg"
hdiutil create -volname "Onyx Agent" -srcfolder "$OUT/OnyxAgent-$VERSION-macos-universal.pkg" -ov -format UDZO "$OUT/OnyxAgent-$VERSION-macos-universal.dmg"
shasum -a 256 "$OUT/OnyxAgent-$VERSION-macos-universal.pkg" "$OUT/OnyxAgent-$VERSION-macos-universal.dmg" > "$OUT/OnyxAgent-$VERSION-macos-universal.sha256.txt"
