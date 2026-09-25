#!/bin/bash
set -euo pipefail

app_dir="$(cd -P "$(dirname "$0")" && pwd)"
cd "$app_dir"

iconset_dir="$app_dir/.build/AppIcon.iconset"
mac_icon="$app_dir/app-icon.png"
mkdir -p "$iconset_dir"
for size in 16 32 128 256 512; do
  sips -s format png -z "$size" "$size" "$mac_icon" \
    --out "$iconset_dir/icon_${size}x${size}.png" >/dev/null
  double_size=$((size * 2))
  sips -s format png -z "$double_size" "$double_size" "$mac_icon" \
    --out "$iconset_dir/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$iconset_dir" -o "$app_dir/app-icon.icns"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-dev.txt
npm install --no-audit --no-fund
npm run build
.venv/bin/pyinstaller --noconfirm --windowed --onedir \
  --name 'Fig Backup' \
  --icon "$app_dir/app-icon.icns" \
  --distpath "$app_dir/release" \
  --workpath "$app_dir/.build" \
  --specpath "$app_dir/.build" \
  --add-data "$app_dir/dist:dist" \
  --collect-all playwright \
  --collect-all webview \
  run_app.py

printf 'Built: %s\n' "$app_dir/release/Fig Backup.app"
