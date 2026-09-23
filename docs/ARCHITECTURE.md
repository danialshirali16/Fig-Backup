# Architecture

Fig Backup is a local desktop app in two halves:

```
┌───────────────────────────── pywebview (cocoa) ─────────────────────────────┐
│  React UI (dist/index.html)          │  Python backend                      │
│  src/App.jsx ── window.pywebview.api ┴─▶ figma_backup/app.py (Bridge)       │
│                                       │   ├─ core.py    Figma REST + stores │
│                                       │   └─ browser.py  Playwright/Chromium│
└─────────────────────────────────────────────────────────────────────────────┘
```

The UI never talks to Figma directly. It calls methods on `window.pywebview.api` (the `Bridge`
class in `figma_backup/app.py`), and the Bridge runs all browser work on a single worker thread
(`ThreadPoolExecutor(max_workers=1)`), returning promises to JavaScript.

## Bridge API

| Method | Purpose |
| --- | --- |
| `bootstrap()` | Create support dirs, return `{has_token, downloads, teams, preferences, version}` |
| `save_preferences(changes)` | Persist language/theme/onboarding flags (validated) |
| `save_token(token)` | Validate via `/v1/me`, store to `token.json` (0600); returns `{name}` |
| `discover_teams()` | Headless browser scrape of the team switcher; merges with `teams.json` |
| `add_team(link, name)` | Register a team by URL/ID |
| `folders(team_id)` | v2 Folders API with fallback to legacy v1 Projects API |
| `subfolders(folder_id)` | Child folders; marks HTTP 451 folders unavailable |
| `files(folder_id)` | Files in a folder (v2 or v1 depending on fallback) |
| `open_sign_in()` | Visible Chromium window on figma.com/files for one-time sign-in |
| `start_download(selection)` | Start one backup; scopes: `{team, scope:'team'}` / `{scope:'folder', folder}` / `{scope:'file', folder, file_key}` |
| `stop_download()` | Ask the current run to stop after the active file |
| `status()` | Snapshot `{running, phase, items, total, saved, existing, skipped, failed, message, destination, finished}` |
| `open_destination()` / `open_downloads()` | Reveal folders in Finder |

`start_download` supports a **single scope per call**. Multi-select backups are implemented in the
UI as a sequential queue of per-item `start_download` calls (see “Backup queue” below).

## Figma client (`core.py`)

- **Folder API strategy**: try v2 `folders`; on 403/404 fall back to legacy v1 `projects`, and
  remember the choice per client (`folder_api`). Subfolder listing may return HTTP 451
  (region/policy restriction); the client records the folder in `unavailable_subfolders` and the UI
  warns the backup may be incomplete.
- **Retries**: 429/5xx retry up to 6 times honoring `retry-after` (clamped 1–60s), exponential
  backoff otherwise.
- **Recursion**: `walk_tree(roots)` returns deduplicated files (each tagged with its ancestor
  folder path) plus every visited folder path — used for team/folder backups and archive
  pre-creation.
- **editorType check**: files whose editor type is not `figma` (e.g. FigJam) are skipped.
- `verify_fig(path)` rejects files ≤ 1 KB or HTML/JSON error responses.

## Browser automation (`browser.py`)

- Launches a **persistent Chromium context** (profile in the legacy support folder) so the Figma
  session survives restarts. Headless for all background work; a visible window only for the
  one-time sign-in.
- Headless runs set a real Chrome user agent (derived from the installed Chromium version) and
  neutralize `navigator.webdriver`.
- **Save local copy** flow: keyboard shortcut `Cmd+/` → quick-action search → “save local copy”;
  fallback path: main menu → File → Save local copy. On failure a screenshot is written to the
  support folder for debugging.
- Detects login redirects and HTTP 403 and raises actionable errors; the UI routes these back to
  the wizard’s sign-in step.

## State & storage

| Path | Contents |
| --- | --- |
| `~/Library/Application Support/Fig Backup/` | `token.json` (0600), `preferences.json`, `archive-roots.json`, `archives/<team>/paths.json`, runtime `venv/` (launcher) |
| `~/Library/Application Support/Figma Fig Downloader/` | Legacy `teams.json`, `downloads.json` index, Chromium profile — reused for compatibility |
| `~/Downloads/Fig Backup/<Team>/…` | Tree backups (folder structure preserved, stable collision-safe names) |
| `~/Downloads/*.fig` | Single-file downloads |

`preferences.json` holds `{language: "en"|"fa", theme: "system"|"light"|"dark",
onboarding_complete: bool}`. English is the default; the setup wizard has no language step.

## Frontend (`src/App.jsx`)

### Views

`wizard` (setup) → `teams` → `browse` → `settings`. The content column is capped at **680px**
(`max-w-[680px]`); the window is 960×700. There is no sidebar — navigation is the breadcrumb
(Teams is the root) plus a predictable Back button.

### Setup wizard (2 steps)

1. **Access token** — save + verify via `/v1/me`; shows “Token verified for *name*”.
2. **Browser sign-in** — “Open sign-in window” then “I've signed in”, or **I'll sign in later**
   (finishes setup; the app still works, and the first sign-in-dependent failure routes back to
   this step with step 1 shown complete). *Redo setup* lives in Settings.

The wizard is shown when `onboarding_complete` is false or no token is stored. A returning user
lands directly in Teams.

### Selection model (multi-select)

- Selection lives **per team**: `selection[teamId] = { folders: Folder[], files: {key, name, folder}[] }`.
  Selecting a folder means *that folder recursively*; loose files remember their parent folder so
  `scope: 'file'` downloads can target the right place. Switching teams switches the selection
  store; nothing is silently dropped.
- **Select mode** is explicit: the toolbar *Select* button swaps per-row actions for checkboxes
  (folder navigation moves to an explicit “Open” chevron so a click never does two things).
  *Done* or **Esc** exits and returns focus to the Select button.
- **Select-all** is a tri-state checkbox (`aria-checked="mixed"`): at a folder level it covers
  that folder’s visible subfolders + loose files; at the team root it covers the whole team.
  Partial selection shows the indeterminate dash.

### Backup queue

`startSelectionBackup()` converts the selection into an ordered item list (folders first, then
files) and runs them **sequentially**: for each item, call `start_download`, then poll `status()`
every 400 ms until `finished`. Additional selections can join the active queue. Item statuses:
`queued → running → done | failed | stopped`. A failure whose
message mentions sign-in marks the item failed with “Sign-in required”, stops the loop, and routes
to the wizard sign-in step; the download manager offers **Retry & continue**. Per-item *Retry*, *Cancel
remaining*, and *Stop after current* are available in the popover.

The **download manager popover** in the top bar shows the live run (progress ring, honest percent —
skipped/failed items are not counted as done — and current file), followed by one row per queue
item (`Team`/`Folder`/`File` chip, name, status, error detail). The destination path appears above
the list. Closing the popover does not stop the queue, and the selection pill hides while it is open.

### Honest percentage

`percentage = done / total` where `done` counts only `saved`/`exists`/`renamed`. Skipped and
failed items are surfaced as badges, never folded into the percentage.

## Design system

- **Tokens**: `src/figma-theme.css` carries the Figma color tokens verbatim (light on `:root`,
  dark on `:root.dark`). `src/index.css` maps shadcn semantic variables onto them and derives
  contrast-safe button, brand-text, muted-text and status colors from the Figma tokens.
  Font: `'Inter', 'Helvetica', sans-serif` (the library’s `--font-family` token).
- **Components**: official shadcn/ui base components (radix) from tag `shadcn@4.21.0` plus the
  official `styles/style-nova.css` layer (imported `layer(base)`, `.style-nova` on `<html>`).
  Nova shape language: h-8 buttons without shadows, `ring-[3px]` focus, ring-1 cards, pill badges,
  and a 3px progress-ring stroke.
- **Tailwind v4** through `@tailwindcss/vite`; opacity modifiers work on the var-based tokens via
  `color-mix`. JSX is compiled by esbuild with `jsx: 'automatic'`; `@` aliases to `src/`.
- **RTL**: logical properties throughout, mirrored chevrons (`rtl:-scale-x-100`), width-based
  progress indicator, flipped progress fill and select-item indicator via two CSS patches in
  `index.css`.

## Packaging

`build-mac.sh` runs PyInstaller (`--windowed --onedir --icon app-icon.icns`) with the built
`dist/` embedded as data and `playwright`/`webview` collected. `app-icon.icns` is generated from
the opaque `app-icon-macos.png` with `sips` + `iconutil` on every build. The original
`app-icon.png` remains the artwork source; the macOS variant fills transparent corners to
avoid the system's padded icon fallback.

On Cocoa, `app.py` extends the content view into a transparent titlebar and hides the duplicate
native title while retaining the standard window controls. The web header supplies drag regions;
its layout leaves room for the controls at narrow window widths.

## Tests

`python -m unittest discover -s tests` covers the core bridge logic (preferences/token stores,
archive naming/collisions, legacy fallback, 451 handling, queue totals, browser-retry path) with
mocked API/browser doubles. `tests/test_app.py` additionally imports Playwright, so it needs the
project venv.
