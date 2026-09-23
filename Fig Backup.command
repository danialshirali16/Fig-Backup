#!/bin/bash
set -euo pipefail
umask 077

app_dir="$(cd -P "$(dirname "$0")" && pwd)"
runtime_dir="${HOME}/Library/Application Support/Fig Backup"
venv_dir="${runtime_dir}/venv"

finish() {
  status=$?
  if [[ $status -ne 0 ]]; then
    printf '\nFig Backup exited with error code %s.\n' "$status"
    if [[ -t 0 ]]; then read -r -p 'Press Enter to close this window... ' _; fi
  fi
}
trap finish EXIT

if [[ ! -f "$app_dir/dist/index.html" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    printf 'The interface is not built. Install Node.js 22+ and try again.\n' >&2
    exit 1
  fi
  printf 'Building the interface…\n'
  (cd "$app_dir" && npm install --no-audit --no-fund && npm run build)
fi

if [[ ! -x "$venv_dir/bin/python" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'Python 3.9+ is required. Install Python and try again.\n' >&2
    exit 1
  fi
  mkdir -p "$runtime_dir"
  printf 'Installing Python dependencies…\n'
  python3 -m venv "$venv_dir"
  "$venv_dir/bin/python" -m pip install --disable-pip-version-check -r "$app_dir/requirements.txt"
fi

printf 'Checking Chromium…\n'
"$venv_dir/bin/python" -m playwright install chromium
cd "$app_dir"
"$venv_dir/bin/python" -m figma_backup.app
