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
| `bootstrap()` | Create support dirs, return `{has_token, downloads, teams, preferences, browser, version}`; `browser.source` identifies installed Chrome/Edge or bundled Chromium. If none is available, proactively submit Chromium installation |
| `save_preferences(changes)` | Persist language and theme; setup completion cannot be set here |
| `begin_setup()` | Invalidate prior completion and require all three checks again |
| `save_token(token)` | Validate via `/v1/me`, store to `token.json` (0600); returns `{name}` |
| `verify_browser()` / `verify_token()` | Prove the headless browser launches and validate a stored token before advancing Setup |
| `complete_setup()` | Verify the browser session, then persist setup version 2 and unlock downloads |
| `install_browser()` | Run the one-time Playwright Chromium install on the worker thread; guarded (`{started: false}` while already installing) |
| `discover_teams()` | Headless browser scrape of the team switcher; merges with `teams.json` |
| `add_team(link, name)` | Register a team by URL/ID |
| `folders(team_id)` | v2 Folders API with fallback to legacy v1 Projects API |
| `subfolders(folder_id)` | Child folders; marks HTTP 451 folders unavailable |
| `files(folder_id)` | Files in a folder (v2 or v1 depending on fallback). Returns as soon as the listing arrives, with every **already known** `editorType` applied from the on-disk cache — the listing itself never carries the type |
| `file_types(keys)` | Resolves the file-type icons for a listing that is already on screen (4 parallel workers, one `/v1/files/:key/meta` per still-unknown key, then one cache flush). Answers **every** requested key, `null` where the type could not be read, so the UI can tell "still loading" from "unknown"; a confirmed HTTP 429 drops the rest and the icons fall back |
| `open_sign_in()` / `close_sign_in()` | Opens a visible Chrome/Edge or bundled Chromium window only on explicit sign-in; closes it before session verification |
| `start_download(selection)` | Start one backup; scopes: `{team, scope:'team'}` / `{scope:'folder', folder}` / `{scope:'file', folder, file_key}` |
| `stop_download()` | Ask the current run to stop after the active file |
| `status()` | Snapshot `{running, phase, items, total, saved, existing, skipped, failed, message, destination, finished, browser}` |
| `open_destination()` / `open_downloads()` | Reveal folders in Finder |
| `open_path(path)` | Reveal one downloaded file in Finder/Explorer (or open its folder); must live under Downloads |

`start_download` supports a **single scope per call**. Multi-select backups are implemented in the
UI as a sequential queue of per-item `start_download` calls (see “Backup queue” below).

## Figma client (`core.py`)

- **Folder API strategy**: try v2 `folders`; on 403/404 fall back to legacy v1 `projects`, and
  remember the choice per client (`folder_api`). Subfolder listing may return HTTP 451
  (region/policy restriction); the client records the folder in `unavailable_subfolders` and the UI
  warns the backup may be incomplete.
- **Retries**: a dropped connection or a read timeout is retried twice with a short backoff
  (0.5s, 1s) and then surfaces as `FigmaError("Could not reach Figma: <Exception>.")` — a blip
  is usually momentary, and library internals never reach the user. This is deliberately separate
  from the server-side loop below, which backs off for minutes on purpose.
- **Error messages** are written to be readable on their own (`Figma refused the request (HTTP
  403): Not authorized.`) rather than exposing the endpoint, because the UI classifies them by
  wording — see `src/api-errors.js`.
- **Retries**: 429/5xx retry up to 6 times honoring `retry-after` (clamped 1–60s), exponential
  backoff otherwise.
- **One pooled connection**: the client holds a `requests.Session` (tests inject their own
  `request_get` instead). A folder browse is one call per file, and a fresh TLS handshake per call
  was a large share of its latency.
- **Editor-type cache**: neither the v2 folder listing nor the v1 project listing carries
  `editorType`, so a type costs one `/meta` call. Resolved types are kept in
  `APP_SUPPORT/editor-types.json` (capped at 5000 keys, written once per batch) and read back
  without any network call, which makes a second visit to a folder instant. A file's type rarely
  changes, so a stale entry costs at most a wrong-looking icon.
- **Recursion**: `walk_tree(roots)` returns deduplicated files (each tagged with its ancestor
  folder path) plus every visited folder path — used for team/folder backups and archive
  pre-creation.
- **403 is not a session failure**: when the editor returns HTTP 403 for a file, that file fails and
  the run continues — it is usually file-level access, or Figma blocking the background browser. Only
  a redirect to the login *route* (first path segment `login` / `signin` / `signup` / `password`,
  so a file merely named "login" cannot trigger it) raises `BrowserAuthError`, which is the one signal
  that ends the queue. Treating a per-file 403 as a dead session used to abort the remaining queue
  *and* reset the user's completed setup, because routing to the wizard calls `begin_setup()`.
- **editorType check**: only supported editor types (Figma Design, FigJam, Slides) are downloaded;
  each editor opens under its own route (`/design/`, `/file/` → redirects to `/board/` for FigJam,
  `/slides/`), and any other file type is skipped with its type noted in the queue. Each editor's
  "Save local copy" yields its own native container — `.fig`, `.jam` (FigJam), `.deck` (Slides) —
  and downloads are named and verified accordingly. FigJam boards can crash the headless browser
  on first attempt; the retry opens the next installed browser or bundled Chromium. A bundled
  Chromium crash retries with its headless shell.
- `verify_fig(path)` rejects files ≤ 1 KB or HTML/JSON error responses.

## Browser automation (`browser.py`)

- Tries installed Chrome, then Edge, using a separate persistent profile for each. Their Figma
  sessions survive restarts without touching the user's normal browser profile. Browser work is
  headless except for one-time sign-in initiated by the user. That window closes when setup ends.
  If a system browser fails to launch or crashes, try the
  next installed browser, then bundled Chromium.
- **Fallback install**: Chromium and its headless shell are not bundled. `chromium_ready()` checks
  the pinned revision, executable, and `INSTALLATION_COMPLETE` marker for both builds; `bootstrap()` submits
  the install proactively only when no system browser and no complete fallback are available,
  exposed as a separate `browser` state dict
  (`ready | missing | setting_up | failed` — separate from the download state because
  `start_download` replaces that dict). `Browser.open()` keeps its own lazy install as the safety
  net. The installer reuses complete caches, repairs the earlier headless-shell cache name,
  and falls back to `playwright install` when mirrors fail. Subprocesses pass
  `CREATE_NO_WINDOW` on Windows so the windowed exe never flashes a console.
- Headless runs set a real Chrome user agent (derived from the active browser version) and
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
| `~/Library/Application Support/Figma Fig Downloader/` | Legacy `teams.json`, `downloads.json` index, bundled Chromium profile, and separate Chrome/Edge profiles |
| `~/Downloads/Fig Backup/<Team>/…` | Tree backups (folder structure preserved, stable collision-safe names) |
| `~/Downloads/*.fig` | Single-file downloads (also `.jam` / `.deck` for FigJam and Slides) |

Both archive indexes are keyed by file key and remember the path they chose, so a repeat backup
skips the browser entirely. That memory outlives an editor-format change, so `target()` repairs an
entry whose extension disagrees with the file's actual editor type instead of failing: the recorded
`.fig` for a FigJam or Slides file is re-pointed to `.jam` / `.deck` (same folder, same stem, still
collision-safe) and the corrected name is written back. Without this the bad entry is re-read on
every launch and every Retry fails identically — the legacy `downloads.json` is shared with the
older Figma Fig Downloader, which named everything `.fig`.

`preferences.json` holds `{language: "en"|"fa", theme: "system"|"light"|"dark",
onboarding_complete: bool}`. English is the default; the setup wizard has no language step.

## Frontend (`src/App.jsx`)

### Views

`wizard` (setup) → `teams` → `browse` → `settings`. The content column is capped at **680px**
(`max-w-[680px]`); the window is 960×700. There is no sidebar — navigation is the breadcrumb
(Teams is the root) plus a predictable Back button.

### Setup wizard (3 required steps)

1. **Browser** — launch the installed Chrome/Edge or fallback Chromium headlessly to prove it works.
   Download status and retry appear here when the fallback is needed.
2. **Access token** — save and verify a new token via `/v1/me`, or reverify a stored token.
3. **Browser sign-in** — open a visible sign-in window only on request, then verify that its saved
   session reaches the authenticated Figma files page in headless mode. A failed check stays on
   this step. The sign-in window closes before verification. *Redo setup* lives in Settings.

The wizard is shown when `onboarding_complete` is false, no token is stored, or the saved
`setup_version` predates the required flow. Only `complete_setup()` sets completion and version 2
after all three checks; `start_download()` rejects incomplete setup. A returning verified user
lands directly in Teams.
Replacing a previously verified token invalidates completion and starts the wizard again.

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
`queued → running → done | partial | skipped | failed | stopped`. A run with only unsupported
files is skipped; a run with both saved and skipped files is partial. A failure whose
message mentions sign-in marks the item failed with “Sign-in required”, stops the loop, and routes
to the wizard sign-in step; the download manager offers **Retry & continue**. Per-item *Retry*, *Cancel
remaining*, and *Stop after current* are available in the popover.

The **download manager popover** in the top bar shows the live run (progress ring, honest percent —
skipped/failed items are not counted as done — and current file), followed by one row per queue
item (`Team`/`Folder`/`File` chip, name, status, error detail). The destination path appears above
the list. Closing the popover does not stop the queue, and the selection pill hides while it is open.

### Honest percentage

The queue progress bar counts only files with `saved`, `exists`, or `renamed` status. A finished
selection contributes `filesDone / filesTotal`; a fully successful or empty-folder selection
contributes one complete queue item. Skipped and failed files do not increase the percentage.

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
`app-icon.png` with `sips` + `iconutil` on every build; `app-icon.png` is the artwork source for
both the macOS variant and the multi-size Windows `.ico`.

On Cocoa, `app.py` extends the content view into a transparent titlebar and hides the duplicate
native title while retaining the standard window controls. The web header supplies drag regions;
its layout leaves room for the controls at narrow window widths. On Windows the window is created
`frameless`: the web header becomes the titlebar — caption buttons (`minimize_window`,
`toggle_maximize_window`, `close_window`) render at its trailing edge, double-click toggles
maximize (state mirrored back via the `maximized`/`restored` events), invisible edge strips call
`begin_resize` to hand the mouse to the native sizing loop, and the `pywebview-drag-region`
header moves the window.

## Tests

`python -m unittest discover -s tests` covers the core bridge logic (preferences/token stores,
archive naming/collisions, legacy fallback, 451 handling, queue totals, browser-retry path) with
mocked API/browser doubles. `tests/test_app.py` additionally imports Playwright, so it needs the
project venv.
