<p align="center">
  <img src="docs/screenshots/icon-256.png" width="88" alt="Fig Backup icon">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <strong>Native <code>.fig</code> backups from Figma — free, local, one click.</strong><br>
  A desktop app for Apple&nbsp;Silicon Macs and Windows&nbsp;10/11.
</p>

<p align="center">
  <a href="#license"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-informational">
  <a href="https://github.com/danialshirali16/Fig-Backup-Mac/actions/workflows/windows-build.yml?query=branch%3Awindows-build"><img alt="Windows build" src="https://github.com/danialshirali16/Fig-Backup-Mac/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

---

Fig Backup saves real, native `.fig` copies of your Figma files — with your folder structure
preserved — straight into your Downloads folder. It is a **local desktop app**: nothing is uploaded
anywhere, and your token stays on your machine.

## Screenshots

<!-- Drop the PNGs into docs/screenshots/ with these exact names and they render automatically:
     setup-wizard.png · browse-select.png · download-manager.png · persian-dark.png
     The app window is 960×700 — PNG at 2× (1920×1400) looks crispest. -->

| Setup wizard | Select mode & the backup pill |
| --- | --- |
| <img src="docs/screenshots/setup-wizard.png" alt="Setup wizard — access token step"> | <img src="docs/screenshots/browse-select.png" alt="Browsing a team in Select mode with the floating backup pill"> |
| **Download manager** | **فارسی · تیره (RTL)** |
| <img src="docs/screenshots/download-manager.png" alt="Download manager popover with a finished backup"> | <img src="docs/screenshots/persian-dark.png" alt="Browse view in Persian (RTL) with the dark theme"> |

## Why?

The Figma REST API cannot export native `.fig` files — the only official way to get one is the web
editor's *Save local copy* action. Fig Backup automates that workflow for you with a bundled
Chromium browser, so what lands on your disk is the same file the Figma editor produces. Pick a
team, choose folders and files, and keep working while the backup runs in the background.

## Features

- **Two-step setup wizard** — *Access token → Browser sign-in*. The one-time browser sign-in is a
  hard requirement for native `.fig` exports, so it is part of setup ("I'll sign in later" works
  too; the first backup routes you back if needed). Re-run it anytime via *Settings → Redo setup*.
- **Multi-select backups** — toggle *Select* to pick any combination of folders (backed up
  recursively) and loose files of a team, then start one backup from the floating pill. While a
  backup runs, new selections join the queue.
- **Non-blocking download manager** — a popover in the top bar shows progress, the current file,
  and one row per queued item with per-item *Retry*, *Stop after current*, and confirmed
  *Cancel remaining*. The rest of the app stays usable while a backup runs.
- **Structure-preserving archives** — team/folder backups land in
  `Downloads/Fig Backup/<Team>/<Folder>/…`; single files go flat into `Downloads`. Duplicates
  become `name(1).fig`, `name(2).fig`, …
- **Light / dark / system themes**, English (default) with full Persian RTL, reduced-motion
  support, and keyboard-accessible selection controls.

## Download

Grab the latest build from the
[**Releases page**](https://github.com/danialshirali16/Fig-Backup-Mac/releases).

| | |
| --- | --- |
| **macOS** (Apple Silicon) | Double-click `Fig Backup.app`. Builds are unsigned, so macOS shows a Gatekeeper warning: right-click the app and choose *Open*, or allow it under System Settings → Privacy & Security. |
| **Windows** (x64) | Unpack and run `Fig Backup.exe`. Needs the WebView2 runtime, which is preinstalled on Windows 10/11. |

On first launch the app downloads Chromium once (~150 MB) for its backup browser — an internet
connection is required for that. Everything else runs locally: backups talk only to Figma, nothing
else.

## Getting started

1. **Create a Figma Personal Access Token** with `folders:read` and `file_metadata:read` scopes
   (Figma → Settings → Security → Personal access tokens). Older PATs with `projects:read` also
   work; the app falls back to the legacy Projects API automatically.
2. **Paste the token** into the setup wizard. It is verified against Figma and saved locally.
3. **Sign in to figma.com once** in the window the app opens — after that, backups run headless in
   the background with no visible browser. You can postpone this step; the app routes you back
   before the first backup if the session is missing.
4. **Pick a team** → *Download all*, or use *Select* to choose folders/files and back them up
   together.

### Where your backups go

| What | Where |
| --- | --- |
| Team / folder backups | `~/Downloads/Fig Backup/<Team>/<Folder>/…` |
| Single files | `~/Downloads/<name>.fig` — duplicates become `name(1).fig`, `name(2).fig`, … |

If Figma restricts subfolder listing for your region (HTTP 451), the app warns you that the backup
may be incomplete.

## Security & privacy

- **Everything is local.** Fig Backup talks only to Figma — it never uploads your files or token
  anywhere else, and there is no telemetry.
- The token is stored at `~/Library/Application Support/Fig Backup/token.json` with file
  permissions `0600` inside a `0700` folder. It is **not** stored in the system keychain and
  **not** separately encrypted — do not use a shared macOS user account. For scripted launches, a
  `FIGMA_PAT` environment variable overrides the saved file at startup.
- Fig Backup does not read or delete a token saved by the old shell tool in Keychain; enter the
  token once in the app.
- The Chromium profile and download index at
  `~/Library/Application Support/Figma Fig Downloader/` are reused from the earlier shell tool for
  compatibility.

## Disclaimer

Fig Backup is an independent, open-source tool and is **not affiliated with, endorsed by, or
connected to Figma**. It relies on the Figma web editor's interface, which may change at any time
and require app updates. Only use Fig Backup with files you are authorized to access, and keep
backups of anything important — this tool is provided as is, without warranty.

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

Python 3.9+ is required. Node.js 22+ is needed only to build the interface — `dist/` ships
prebuilt, so Node is only needed after UI changes.

- Alternatively, double-click `Fig Backup.command`; it creates a Python environment, installs
  missing dependencies, and launches the desktop app.
- **UI review in a browser**: run `npm run dev` and open
  [http://127.0.0.1:5173/?preview=1](http://127.0.0.1:5173/?preview=1) — a development-only view
  with sample teams and folders. It never connects to Figma or starts real backups.
- **Packaging**: `./build-mac.sh` builds an Apple Silicon app into `release/` (regenerates
  `app-icon.icns` from `app-icon-macos.png`). `./build-windows.sh` (from Git Bash; Node 22+,
  Python 3.11+) builds `release/Fig Backup/Fig Backup.exe`. No account credentials are bundled
  into the app. Public releases need code-signing and notarization to avoid Gatekeeper warnings.

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
tests/                   Python unit tests (core bridge logic) + a JS test for download errors
build-mac.sh / build-windows.sh   PyInstaller packaging scripts (macOS / Windows)
Fig Backup.command       User launcher (creates venv, installs deps, runs app)
docs/                    ARCHITECTURE.md, UI.md, screenshots/
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — backend/frontend split, bridge API, storage
  layout, backup-queue semantics.
- [docs/UI.md](docs/UI.md) — screens and flows, selection model, design system (tokens,
  components), i18n and accessibility.

## Contributing

Bug reports, fixes, and features are welcome — open an issue or a pull request. Development setup
is above. Two conventions to know before you start:

- New UI strings must be added to **both** languages in `src/i18n.js` (`en` and `fa`).
- The built `dist/` is tracked in git on purpose (the `.command` launcher and packaged apps rely on
  it) — after changing the UI, run `npm run build` and commit the result.

## License

[MIT](LICENSE) — free to use, modify, and redistribute.

## Acknowledgments

- [pywebview](https://pywebview.flow.dev/) — the native window and Python↔JS bridge
- [Playwright](https://playwright.dev/) — Chromium automation
- [shadcn/ui](https://ui.shadcn.com) (nova style) + [Radix UI](https://www.radix-ui.com/) — interface components
- Figma design tokens from [@create-figma-plugin/ui](https://github.com/figma-community/create-figma-plugin)
- [lucide-react](https://lucide.dev/) — icons
