#!/bin/bash
set -euo pipefail

app_dir="$(cd -P "$(dirname "$0")" && pwd)"
cd "$app_dir"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-dev.txt
npm install --no-audit --no-fund
npm run build
.venv/bin/pyinstaller --noconfirm --windowed --onedir \
  --name 'Fig Backup' \
  --distpath "$app_dir/release" \
  --workpath "$app_dir/.build" \
  --specpath "$app_dir/.build" \
  --add-data "$app_dir/dist:dist" \
  --collect-all playwright \
  --collect-all webview \
  run_app.py

printf 'Built: %s\n' "$app_dir/release/Fig Backup.app"
