#!/bin/bash
# Windows build (run from Git Bash on a Windows machine with Node 22+ and Python 3.11+).
# Produces release/Fig Backup/Fig Backup.exe (onedir, windowed).
set -euo pipefail

app_dir="$(cd -P "$(dirname "$0")" && pwd)"
cd "$app_dir"
win_dir="$(cygpath -m "$app_dir")"

if [[ ! -x .venv/Scripts/python.exe ]]; then
  python -m venv .venv
fi
.venv/Scripts/python.exe -m pip install --disable-pip-version-check -r requirements-dev.txt
npm install --no-audit --no-fund
npm run build
.venv/Scripts/python.exe -m PyInstaller --noconfirm --windowed --onedir \
  --name 'Fig Backup' \
  --icon "$win_dir/app-icon-windows.ico" \
  --distpath "$win_dir/release" \
  --workpath "$win_dir/.build" \
  --specpath "$win_dir/.build" \
  --add-data "$win_dir/dist;dist" \
  --collect-all playwright \
  --collect-all webview \
  run_app.py

printf 'Built: %s\n' "$win_dir/release/Fig Backup/Fig Backup.exe"
