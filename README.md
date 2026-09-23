# Fig Backup for macOS

Fig Backup creates native `.fig` backups from Figma in `~/Downloads`. It is a free local desktop app with a Python backend, Playwright/Chromium for Figma's **Save local copy** action, and an English (default) / Persian (RTL) interface built with React 18, Tailwind CSS v4, and [shadcn/ui](https://ui.shadcn.com) (nova style) themed with Figma's own design tokens.

## Features

- **Two-step setup wizard** — *Access token → Browser sign-in*. The browser session is a hard requirement for native `.fig` exports, so it is part of setup instead of a late error. Sign-in can be postponed ("I'll sign in later"); the first backup attempt without a session routes back to that step. Re-run it anytime via *Settings → Redo setup*.
- **Multi-select backups** — toggle *Select* in the browse toolbar to pick any combination of folders (selected recursively) and loose files of a team, then start one backup from the floating pill. During a running backup the pill becomes *Add to queue*.
- **Non-blocking progress** — the **download manager popover** in the top bar shows the progress ring, current file, percent, and one row per queued item (`Team` / `Folder` / `File` chip, per-item status), plus *Retry* per failed item, *Stop after current*, confirmed *Cancel remaining*, and *Open backup folder*.
- **Structure-preserving archives** — team/folder backups land in `Downloads/Fig Backup/<Team>/<Folder>/…`; single-file downloads go flat into `Downloads`. Duplicate names become `name(1).fig`, `name(2).fig`, …
- **Light / dark / system themes**, English default with full Persian RTL, reduced-motion support, and keyboard-accessible selection controls.

## Run

Double-click **Fig Backup.app** on an Apple Silicon Mac. The app bundles Python and its interface. If Chromium is missing, the app installs it in the Playwright browser cache on first use; this requires an internet connection.

Alternatively, double-click **Fig Backup.command** in the source folder. This creates a Python environment and installs missing dependencies before launching the desktop app. Python 3.9+ is required. Node.js 22+ is needed only if the prebuilt `dist/` interface is missing or you want to modify it.

1. Enter a Figma Personal Access Token with `folders:read` and `file_metadata:read` scopes. Older PATs may use `projects:read` with the legacy Projects API.
2. Pick a team, then either *Download all*, or use *Select* to choose folders/files and start a batch backup.
3. If the browser session has expired, the app routes you back to the sign-in step; after one sign-in, downloads run in headless Chromium without visible browser windows.

The token is saved in `~/Library/Application Support/Fig Backup/token.json`, with file permissions `0600` and parent-folder permissions `0700`. For scripted launches, a `FIGMA_PAT` environment variable, when set, is used at startup instead of the saved file. The token is **not stored in Keychain** and is **not independently encrypted**. Do not use a shared macOS user account. Fig Backup does not read or delete a token saved by the old shell tool in Keychain; enter the token once in the new app.

If Figma limits subfolder listing (HTTP 451), the app warns that the backup may be incomplete. The existing download index and Chromium profile at `~/Library/Application Support/Figma Fig Downloader/` are reused for compatibility with the earlier shell tool.

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

For UI review in a browser, run `npm run dev` and open
`http://127.0.0.1:5173/?preview=1`. This development-only view uses sample
teams and folders; it does not connect to Figma or start real backups.

Run `./build-mac.sh` to create an Apple Silicon app in `release/` (bundles `app-icon.icns`). Public GitHub releases need code-signing and notarization to avoid Gatekeeper warnings. No account credentials are bundled into the app.

Only use Fig Backup with files you are authorized to access. Figma's web UI may change, so the browser automation may need maintenance. The Figma REST API does not provide native `.fig` exports; this app uses the web editor's local-copy workflow.

## Project structure

```
figma_backup/            Python backend (pywebview bridge, Figma API, browser automation)
  app.py                 pywebview window + Bridge exposed to the UI (js_api)
  core.py                Figma REST client, token/preferences stores, archive indexes
  browser.py             Playwright/Chromium automation of "Save local copy"
src/                     React interface (built with Vite into dist/)
  App.jsx                All screens: setup wizard, teams, browse, settings, queue
  i18n.js                English/Persian copy + translate()
  index.css              Tailwind v4 entry, shadcn tokens mapped to Figma tokens
  figma-theme.css        Figma color tokens (light/dark), from @create-figma-plugin/ui
  styles/style-nova.css  Official shadcn "nova" style layer
  components/ui/         shadcn base components (radix)
app-icon.png            Original icon artwork
app-icon-macos.png      Opaque, full-bleed icon for macOS app packaging
tests/                   Python unit tests (core bridge logic)
app-icon.icns            macOS app icon (regenerated from app-icon-macos.png by build-mac.sh)
build-mac.sh             PyInstaller packaging script
Fig Backup.command       User launcher (creates venv, installs deps, runs app)
docs/ARCHITECTURE.md     How the pieces fit together
docs/UI.md               Screens, flows, design system, accessibility
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — backend/frontend split, bridge API, storage layout, backup queue semantics.
- [docs/UI.md](docs/UI.md) — screens and flows, selection model, design system (tokens, components), i18n and accessibility.
