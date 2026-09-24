<p align="center">
  <img src="docs/screenshots/icon-256.png" width="88" alt="Fig Backup icon">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <strong>Native <code>.fig</code> backups from Figma — free, local, one click.</strong><br>
  A desktop app for Apple&nbsp;Silicon Macs and Windows&nbsp;10/11.
</p>

<!-- Language switcher: add one link per translated README next to "English", e.g.
     English · <a href="README.fa.md">فارسی</a> · <a href="README.de.md">Deutsch</a> -->

<p align="center">
  <a href="#license"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-informational">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build"><img alt="Windows build" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

---

Fig Backup saves real, native `.fig` copies of your Figma files — with your folder structure
preserved — straight into your Downloads folder. It is a **local desktop app**: nothing is uploaded
anywhere, and your token stays on your machine.

## Screenshots

<!-- Drop the PNGs into docs/screenshots/ with these exact names and they render automatically:
     setup-wizard.png · browse-select.png · download-manager.png · dark-mode.png
     The app window is 960×700 — PNG at 2× (1920×1400) looks crispest. -->

| Setup wizard | Select mode & the backup pill |
| --- | --- |
| <img src="docs/screenshots/setup-wizard.png" alt="Setup wizard — access token step"> | <img src="docs/screenshots/browse-select.png" alt="Browsing a team in Select mode with the floating backup pill"> |
| **Download manager** | **Dark mode** |
| <img src="docs/screenshots/download-manager.png" alt="Download manager popover with a finished backup"> | <img src="docs/screenshots/dark-mode.png" alt="Browse view with the dark theme"> |

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

## Download

Grab the latest build from the
[**Releases page**](https://github.com/danialshirali16/Fig-Backup/releases).

| | |
| --- | --- |
| **macOS** (Apple Silicon) | Double-click `Fig Backup.app`. Builds are unsigned, so macOS shows a Gatekeeper warning: right-click the app and choose *Open*, or allow it under System Settings → Privacy & Security. |
| **Windows** (x64) | Unpack and run `Fig Backup.exe`. Needs the WebView2 runtime, which is preinstalled on Windows 10/11. |

On first launch the app downloads Chromium once (~150 MB) for its backup browser — an internet
connection is required for that. Everything else runs locally: backups talk only to Figma, nothing
else. Problems installing or signing in? See
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

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

## Contributing

Bug reports, fixes, and features are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and project conventions (run the
tests, add UI strings to every language in `src/i18n.js`, and rebuild `dist/` after UI changes).

## License

[MIT](LICENSE) — free to use, modify, and redistribute.

## Donate

If Fig Backup saves you time, you can support its development with Bitcoin:

<p align="center">
  <img src="docs/screenshots/donate-qr.png" alt="Bitcoin donation QR code" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>
