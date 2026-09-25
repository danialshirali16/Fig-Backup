# Contributing to Fig Backup

Thanks for your interest in improving Fig Backup! Bug reports, fixes, and features are all
welcome — open an [issue](https://github.com/danialshirali16/Fig-Backup/issues) or a pull request.

## Development setup

macOS or Windows with Python 3.9+ and Node.js 22+ (Node is only needed for UI changes — `dist/`
ships prebuilt):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
npm install
npm run build
.venv/bin/python -m playwright install chromium
```

- **Run the app**: `.venv/bin/python -m figma_backup.app` (Windows: `.venv\Scripts\python -m figma_backup.app`)
- **Run tests**: `.venv/bin/python -m unittest discover -s tests` and `npm run test:node`
  (`tests/test_app.py` imports Playwright, so run the suite from the project venv.)
- **UI review without the backend**: `npm run dev`, then open
  `http://127.0.0.1:5173/?preview=1` — a development-only view with sample data that never touches
  Figma or starts real backups.

## Conventions

- **Interface strings live in `src/i18n.js`.** Every new key must be added to *all* language
  objects there (English and فارسی in `i18n.js`, the other seven in `src/i18n-languages-*.js`) —
  the UI looks up keys in the active language and falls back to English only when a key is
  missing entirely from a language.
- **`dist/` is tracked in git on purpose.** The `Fig Backup.command` launcher and the packaged apps
  load the built interface from it. If you change anything under `src/`, run `npm run build` and
  commit the rebuilt `dist/` in the same change.
- **Docs move with behavior.** User-facing changes belong in `README.md`; architecture and flow
  details in `docs/ARCHITECTURE.md` and `docs/UI.md`.
- Match the style of the surrounding code: the backend is plain Python (stdlib + type hints), the
  interface is React 18 + Tailwind v4 + shadcn/ui (nova).

## Packaging

- macOS: `./build-mac.sh` → `release/Fig Backup.app` (regenerates `app-icon.icns` from
  `app-icon.png` on every build).
- Windows: `./build-windows.sh` from Git Bash (Node 22+, Python 3.11+) →
  `release/Fig Backup/Fig Backup.exe`.

## Releases

Releases are fully automated: push a `vX.Y.Z` tag to `main` and the Release workflow builds both
platforms on GitHub's runners, runs the tests, and publishes `Fig-Backup-macOS.zip`,
`Fig-Backup-Windows-x64.zip`, and a combined `SHA256SUMS.txt` to GitHub Releases with generated
notes (categories in `.github/release.yml`; copy `.github/RELEASE_NOTES_TEMPLATE.md` if you want
a hand-written highlights section). Never upload release assets manually.

## Working with AI coding agents

If you use AI agents in this repo, point them at [.agents/AGENTS.md](.agents/AGENTS.md) — it
collects the project's ground rules (history policy, commit identity, i18n and `dist/`
conventions, and the UI preview/screenshot harness gotchas).

## Reporting bugs

Please include:

- Your OS + version and the Release tag you downloaded.
- Steps to reproduce, and what happened vs. what you expected.
- Any error text shown in the download manager or setup wizard.

**Never paste your Figma access token into an issue.**
