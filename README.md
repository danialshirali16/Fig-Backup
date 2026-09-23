# Fig Backup for macOS

Fig Backup creates native `.fig` backups from Figma in `~/Downloads`. It is a free local desktop app with a Python backend, Playwright/Chromium for Figma's **Save local copy** action, and an English LTR interface using Preact and [`@create-figma-plugin/ui`](https://yuanqing.github.io/create-figma-plugin/ui/).

## Run

Double-click **Fig Backup.app** on an Apple Silicon Mac. The app bundles Python and its interface. If Chromium is missing, the app installs it in the Playwright browser cache on first use; this requires an internet connection.

Alternatively, double-click **Fig Backup.command** in the source folder. This creates a Python environment and installs missing dependencies before launching the desktop app. Python 3.9+ is required. Node.js 22+ is needed only if the prebuilt `dist/` interface is missing or you want to modify it.

1. Enter a Figma Personal Access Token with `folders:read` and `file_metadata:read` scopes. Older PATs may use `projects:read` with the legacy Projects API.
2. Select a team, folder, and one file or **All**.
3. If the browser session has expired, click **Open sign-in window** and sign in once. Click **I've signed in** afterward. Normal discovery and downloads then run in headless Chromium without visible browser windows.

The token is saved in `~/Library/Application Support/Fig Backup/token.json`, with file permissions `0600` and parent-folder permissions `0700`. It is **not stored in Keychain** and is **not independently encrypted**. Do not use a shared macOS user account. Fig Backup does not read or delete a token saved by the old shell tool in Keychain; enter the token once in the new app.

Duplicate filenames become `name.fig`, `name(1).fig`, `name(2).fig`, and so on. The existing download index and Chromium profile at `~/Library/Application Support/Figma Fig Downloader/` are reused for compatibility with the earlier shell tool. If Figma limits subfolder listing (HTTP 451), the app warns that the backup may be incomplete.

## Development

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm install
npm run build
.venv/bin/python -m playwright install chromium
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m figma_backup.app
```

Run `./build-mac.sh` to create an Apple Silicon app in `release/`. Public GitHub releases need code-signing and notarization to avoid Gatekeeper warnings. No account credentials are bundled into the app.

Only use Fig Backup with files you are authorized to access. Figma's web UI may change, so the browser automation may need maintenance. The Figma REST API does not provide native `.fig` exports; this app uses the web editor's local-copy workflow.
