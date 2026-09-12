#!/bin/bash
set -euo pipefail
VERSION="${1:-1.0.2}"
if [[ "${ONYX_ALLOW_UNSIGNED_DEVELOPMENT_BUILD:-}" != "1" ]]; then echo "Set ONYX_ALLOW_UNSIGNED_DEVELOPMENT_BUILD=1 only on an owned development Mac." >&2; exit 2; fi
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; OUT="$ROOT/dist"; STAGE="$ROOT/build/macos-root"
case "$(uname -m)" in arm64) ARCH="arm64";; x86_64) ARCH="x64";; *) echo "Unsupported Mac architecture" >&2; exit 2;; esac
rm -rf "$STAGE"; mkdir -p "$STAGE/Library/Application Support/Onyx/bin" "$STAGE/Library/LaunchDaemons" "$OUT"
python3 -m pip install -r "$ROOT/requirements.txt"; cd "$ROOT"; python3 -m PyInstaller --clean --noconfirm --onefile --name "OnyxAgent-$ARCH" onyx_agent_entry.py
cp "$ROOT/dist/OnyxAgent-$ARCH" "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-$ARCH"; chmod 755 "$STAGE/Library/Application Support/Onyx/bin/OnyxAgent-$ARCH"
cp "$ROOT/packaging/macos/com.onyx.endpoint-agent.plist" "$STAGE/Library/LaunchDaemons/"
pkgbuild --root "$STAGE" --scripts "$ROOT/packaging/macos/scripts" --identifier com.onyx.endpoint-agent --version "$VERSION" --install-location / "$OUT/OnyxAgent-$VERSION-macos-$ARCH.pkg"
hdiutil create -volname "Onyx Agent" -srcfolder "$OUT/OnyxAgent-$VERSION-macos-$ARCH.pkg" -ov -format UDZO "$OUT/OnyxAgent-$VERSION-macos-$ARCH.dmg"
shasum -a 256 "$OUT/OnyxAgent-$VERSION-macos-$ARCH.pkg" "$OUT/OnyxAgent-$VERSION-macos-$ARCH.dmg" > "$OUT/OnyxAgent-$VERSION-macos-$ARCH.sha256.txt"
