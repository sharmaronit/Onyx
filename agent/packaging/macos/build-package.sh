#!/bin/bash
set -euo pipefail
VERSION="${1:-1.0.0}"
if [[ "${ONYX_ALLOW_UNSIGNED_DEVELOPMENT_BUILD:-}" != "1" ]]; then echo "Set ONYX_ALLOW_UNSIGNED_DEVELOPMENT_BUILD=1 only on an owned development Mac." >&2; exit 2; fi
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; OUT="$ROOT/dist"; STAGE="$ROOT/build/macos-root"
rm -rf "$STAGE"; mkdir -p "$STAGE/Library/Application Support/Onyx" "$STAGE/Library/LaunchDaemons" "$OUT"
python3 -m pip install -r "$ROOT/requirements.txt"; cd "$ROOT"; python3 -m PyInstaller --clean --noconfirm --onefile --name OnyxAgent onyx_agent/__main__.py
cp "$ROOT/dist/OnyxAgent" "$STAGE/Library/Application Support/Onyx/OnyxAgent"; chmod 755 "$STAGE/Library/Application Support/Onyx/OnyxAgent"
cp "$ROOT/packaging/macos/com.onyx.endpoint-agent.plist" "$STAGE/Library/LaunchDaemons/"
pkgbuild --root "$STAGE" --scripts "$ROOT/packaging/macos/scripts" --identifier com.onyx.endpoint-agent --version "$VERSION" --install-location / "$OUT/OnyxAgent-$VERSION-macos.pkg"
hdiutil create -volname "Onyx Agent" -srcfolder "$OUT/OnyxAgent-$VERSION-macos.pkg" -ov -format UDZO "$OUT/OnyxAgent-$VERSION-macos.dmg"
shasum -a 256 "$OUT/OnyxAgent-$VERSION-macos.pkg" "$OUT/OnyxAgent-$VERSION-macos.dmg" > "$OUT/OnyxAgent-$VERSION-macos.sha256.txt"
