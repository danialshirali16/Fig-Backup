# Agent guide for Fig Backup

Operating notes for AI coding agents (and humans pairing with them) working in this repository.
Read this before making changes; it encodes decisions the maintainer has already made.

## What this project is

Fig Backup is a local desktop app (macOS Apple Silicon + Windows) that backs up Figma files as
native `.fig` files by automating the web editor's *Save local copy* flow. The Python backend
(`figma_backup/`) sits behind a pywebview bridge; the React 18 + Tailwind v4 + shadcn/ui (nova)
interface lives in `src/` and is built into the tracked `dist/`.

Read first, in this order: `docs/ARCHITECTURE.md` · `docs/UI.md` · `CONTRIBUTING.md` ·
`docs/TROUBLESHOOTING.md`.

## Commands

```sh
# one-time setup
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
npm install
npm run build
.venv/bin/python -m playwright install chromium

# tests (run from the project venv; test_app.py imports Playwright)
.venv/bin/python -m unittest discover -s tests
node --test tests/download-errors.test.js

# run the app / package
.venv/bin/python -m figma_backup.app
./build-mac.sh            # → release/Fig Backup.app
./build-windows.sh        # from Git Bash → release/Fig Backup/Fig Backup.exe
```

## Ground rules (decisions already made — do not relitigate)

1. **Never rewrite git history or force-push.** A filter-repo rewrite was done once at the
   maintainer's request and then reverted the same day; the final decision is that history stays
   as is. Regular commits to `main` only.
2. **Commit identity**: the repo-local git config uses the GitHub noreply email
   (`69107616+danialshirali16@users.noreply.github.com`). Leave it alone.
3. **Run the tests before pushing.** Both the Python suite and the JS download-errors test.
4. **i18n**: every new UI string goes into *all* language objects in `src/i18n.js` — a missing key
   breaks that language.
5. **`dist/` is tracked on purpose** (the `.command` launcher and packaged apps load it). After
   changing anything under `src/`, run `npm run build` and commit the rebuilt `dist/` in the same
   change.
6. **UI work follows `docs/UI.md`**: nova shapes (h-8 buttons, ring-1 cards, pill badges), Figma
   design tokens from `src/figma-theme.css`, logical properties for RTL, the a11y rules listed in
   that doc. Components are official shadcn/ui sources — do not hand-port styles.
7. **Backend is plain stdlib Python with type hints.** All browser work stays on the single worker
   thread in `figma_backup/app.py`; UI-facing state changes go through the Bridge.
8. **Never commit tokens or personal data**, and never include a Figma token in issues, logs, or
   screenshots.
9. **Commit messages** in English, imperative mood, with a short body for non-trivial changes.
10. **Push gotcha**: a push can occasionally report "Everything up-to-date" right after a commit
    without actually updating the ref — verify with `git log origin/main -1` and re-push if needed.

## UI preview & screenshots (no backend needed)

- `npm run dev` → `http://127.0.0.1:5173/?preview=1` serves a mock bridge with sample teams and
  folders. Query flags: `&fresh` (setup wizard), `&browser-install` (fakes the one-time Chromium
  setup state), `&win-titlebar` (fakes the Windows shell caption buttons).
- The app window is **960×700** (min 640×520) — size the browser viewport to match before
  reviewing or screenshotting (2× DPR gives crisp assets).
- Gotcha: the preview bridge always reports `has_token: true`, so the wizard opens at **step 2**.
  For a step-1 view, inject a minimal `window.pywebview` mock (`has_token: false`,
  `onboarding_complete: false`) via Playwright's `add_init_script` before the app loads —
  `installPreviewBridge()` early-returns when a bridge already exists.
- Gotcha: preview preferences reset on page reload. To screenshot a non-default language/theme,
  change them via the in-app Settings and navigate without reloading.
- Chrome DevTools MCP cannot write files outside its workspace roots; prefer Playwright from the
  project `.venv` for scripted screenshots saved into the repo.

## Releases

- **Releases are created exclusively by pushing a `vX.Y.Z` tag to `main`** — the Release workflow
  builds both platforms on GitHub runners, runs the tests, computes `SHA256SUMS.txt`, and
  publishes the GitHub Release. Never build/upload release assets manually.
- Keep `package.json` and the Bridge's `version` string in sync with the tag.
- Notes: the workflow generates notes via `.github/release.yml` categories; edit the release
  afterwards with highlights from `.github/RELEASE_NOTES_TEMPLATE.md` if wanted.
- Checklist before tagging: tests green locally, docs consistent, version strings match.
