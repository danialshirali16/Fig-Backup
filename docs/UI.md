# UI Guide

Screens, flows, and rules of the Fig Backup interface. The implementation lives in
`src/App.jsx`; visual language is Tailwind v4 + shadcn/ui (nova) with Figma design tokens
(see [ARCHITECTURE.md](ARCHITECTURE.md) → Design system).

## Window & layout

- Window: 960×700 (min 640×520). The **content column is capped at 680px**, centered.
- Sticky top bar: “Fig Backup” with *Download manager* (download icon, opens a popover) and *Settings* (gear) on the trailing edge. On Settings, the bar contains only a Back icon and “Settings” title. On macOS it fills the transparent native titlebar; the traffic-light controls stay at the physical left, with extra clearance below 840px.
- No sidebar. Navigation is the **breadcrumb** — `Teams / <Team> / <Folder>…` — rendered in the
  header itself. Every ancestor is a real target, so the user can see where they are and jump up a
  level; *Teams* is always the root exit. The current crumb is the page's `h1`, and long names
  truncate rather than wrap the bar.

## Setup wizard (first run, or Settings → Redo setup)

Shown when there is no stored token or setup was never completed. Three steps with a numbered rail
(done / current / upcoming).

| Step | Contents | Exits |
| --- | --- | --- |
| 1 · Browser | Explains the Chrome → Edge → Chromium fallback. Shows detection, installation progress and retry; *Check browser and continue* launches the chosen browser headlessly before advancing. | Verified browser → Step 2 |
| 2 · Access token | Three numbered instructions explain where to create a token in Figma, which three scopes to enable, and why it must be copied immediately. A button opens Figma settings. The labeled paste field follows; a new or already saved token is verified via `/v1/me`. | Verified token → Step 3 |
| 3 · Browser sign-in | Explains that the visible sign-in window opens only by user action. *Verify sign-in* closes that window and checks the saved session in a hidden browser. Failure remains on this step. | Verified session → Teams |

### One-time browser setup

The app first tries installed Chrome or Edge. If neither is available or usable, it downloads Chromium and its headless build (~325 MB total). Readiness for the fallback requires both pinned revisions, their executables, and completion markers. `setting_up` shows byte progress when the source announces a total and an indeterminate bar otherwise; `failed` shows technical details and *Retry setup*. Status appears in wizard step 1, Teams, and the download manager. After ~5 minutes, the message changes for slower networks. Quitting during setup is safe; the next launch retries incomplete files.

- **Expired sign-in**: a backup run with a missing browser session routes back to step 1 to recheck
  all three requirements. The queue offers *Retry & continue* after setup completes.
- **Language is English by default**; change it in Settings or from the token step. There is no
  language step in the wizard.
- **Redo setup** (Settings) re-opens the wizard at step 1. A saved token can be verified in step 2
  without asking the user to retrieve it again.

## Teams

**Launch never waits for team discovery.** `bootstrap()` returns the cached team list immediately,
so the window paints the real teams as soon as it opens; the browser-backed re-scrape then refreshes
them **in place**, with no skeleton flash over data that is already there. Discovery launches a
browser and reads Figma's team switcher, which can take seconds — gating the whole UI on it left the
window on a bare “Loading…” spinner for that whole time. A failed startup refresh keeps the cached
list and reports a toast; only a launch with no cached teams falls back to the error state with
*Retry*. A manual *Refresh* still shows skeletons, since there is nothing better to show yet.

Borderless list of discovered teams (team avatar, name, chevron). Avatars discovered in the
Figma team switcher are stored locally for display in the app; teams without an available image show
their initial. *Refresh* re-scrapes the team switcher (hidden while the one-time browser setup is
installing — it cannot help). If the browser session is missing, a banner offers *Redo setup*.
During browser setup a status banner takes that slot (“Downloading
the backup browser”, or its danger variant with *Retry setup* on failure); the list area shows
“Finding your teams…” instead of the empty state until setup settles.

Row click → Browse for that team. While the team switcher is being scraped (Refresh or first
launch), the list is replaced by skeleton rows.

## Browse (folders & files)

Header: the breadcrumb on the leading edge, actions on the trailing edge depending on context:

| Context | Actions |
| --- | --- |
| Team root, not selecting | *Download all* (primary) + *Select* |
| Inside a folder, not selecting | *Download all* + *Select* |
| Select mode | *Done* (leaves select mode) |

Entering select mode adds a bar above the list, holding the tri-state **Select-all** checkbox, a
folder-scoped “N of M selected” counter, and a primary **Back up N items** button that queues the
whole selection. The counter counts only what is on screen, because the selection store is per team
and survives navigation: when items are selected in other folders the bar also says how many, with
a *Clear all selections* link. The button label always shows the team-wide total it will queue.
*Done*, Esc, and the bar's own affordances are the only ways out.

Content uses the same borderless, rounded row style as Teams. Folders appear first in alphabetical order, followed by files in
alphabetical order. There are no section headers or download-location note. While a team or folder
listing loads, seven skeleton rows (pulsing tile + two lines, `role="status"`) replace the list —
navigation happens instantly and the data fills in.

A **search field** sits above the list. Filtering is client-side — the listing is already in
memory, so it costs no API call and works offline. Matches are highlighted with the Figma warning
colour, a `role="status"` line reports “N of M”, a folder row states that *Download all* includes
subfolders, and a folder with files shows a *Download* button. The term clears on navigation, since
each folder is a different list. Whatever is filtered out is also unselectable — a user cannot
select a row they cannot see.

The child-folder and file listings are fetched **in parallel**, and a file row does not wait for its
type: Figma's listings never include `editorType`, so resolving one costs an API call per file.
Names, row actions and the select checkboxes are usable as soon as the listing lands, and the
28px tile shows a pulsing placeholder until the type arrives — the row never claims a file is a
Design file before knowing. The type lookup is discarded if the user navigates away first, and a
failure or rate limit simply leaves the Design glyph in place. Types are cached on disk, so a
second visit to the same folder usually shows the right icons with no lookup at all.

- **Not selecting** — clicking a folder row opens it (chevron affordance); per-row buttons offer
  single *Back up* (folder, recursive) and *Download*.
- **Select mode** — every row gets a checkbox replacing its action button; folder rows keep an
  explicit *Open* chevron-link so navigation and selection never collide. Selected rows tint with
  the brand wash.

### Selection rules

- Selection is **per team** and persists while you navigate (including into subfolders). It
  clears when you start a backup from the pill or press its ×.
- Checking a folder selects it **recursively**; the pill counts items as
  “*F* folders · *G* files”. Select-all reflects the visible level: at team root it means the
  whole team, inside a folder it covers that folder’s visible subfolders + loose files. Partial
  coverage shows the indeterminate dash.
- Esc (or *Done*) leaves Select mode and returns focus to the Select button.

### The pill

When a selection exists, a floating pill sits above the bottom edge:

- “*N* items” + “*F* folders · *G* files”
- **Back up *N* items** — or **Add to queue** while another backup is running; new items join
  the current queue without interrupting the active file
- **×** clears the selection

Hidden while the download manager is open.

## Backups: download manager

The download icon in the top bar opens the **Downloads popover** (375px), modelled on a browser
download manager (see the Figma source of truth):

- Header: “Downloads”, a **Clear** button (disabled until something is finished; it removes only
  finished rows — queued and running items are never touched), and close.
- One-time browser setup states render as slim banners between the header and the list (spinner
  card while installing, danger card + full-width *Retry setup* on failure, a one-line “Browser
  ready” flash for 2.5s after success).
- The list is split into three counted sections: **In Progress** (queued, running), **Needs
  attention** (failed, stopped — on a danger-tinted band so a dead run is never read as work still
  in flight), and **Completed** (done). Partial and skipped rows sit with the run that produced
  them. Each row: a 28px icon (the real Figma file icon for files; the team avatar for teams, muted
  `Folder` tile for folders), the name, and a **status caption** underneath —
  “Queue” while queued; the live export stage while running, using the design's exact wording
  (*Opening file... → Downloading assets... → Bundling...*), with “Collecting files…” plus an
  elapsed m:ss counter during the scanning phase, and a “*done* of *total* files” suffix for
  folder/team items; the error text for failures. Only the stage text is in an `aria-live` region,
  so a screen reader hears each stage change without the per-file counter firing on every file.
- A finished row reports **what actually happened**, never a generic success: *Saved* with the byte
  size, *Already saved* when every file was already on disk (an existing file reports no size, so
  no byte count is shown), or *Renamed* when only a legacy name was migrated. Folder and team rows
  combine the file count with the total size, prefixed by *Already saved* when nothing new was
  fetched.
- Trailing per-row actions: queued rows show **Cancel** (remove from queue) and **Download
  next** (play — runs that item first) on hover or keyboard focus; the running row shows a spinner
  that swaps to **Cancel** (stop after current) the same way; completed rows show **Show in folder**
  (reveals the file in Finder/Explorer) on hover; failed/stopped rows always show **Cancel**
  (dismiss the row) and **Retry** (`refresh-cw`); partial and skipped rows offer the same actions.
  Partial rows show the completed file count alongside the unsupported-file notice; skipped rows
  explain that no supported files were found. Failed rows use the danger color —
  the error state per the Figma source of truth. The **Clear** header button renders only while
  completed rows exist.

Starting a download while rows from an earlier run are still listed **keeps anything that can still
be acted on** (failed, stopped, partial, skipped) and its per-row *Retry*; only completed rows are
dropped. Replacing the whole queue outright silently destroyed a failure the user had not seen yet.

Items run **sequentially** (folders first, then files). Closing the popover never affects the run;
Esc closes it and returns focus to the control that opened it. The popover is non-modal, so the rest
of the app remains available while a backup runs. It holds a **400px minimum height** (clamped to
the available height) so it does not resize under the pointer when the first row arrives.

## File name conflicts

The folder listings never carry a file's editor type, but the destination name is known before
anything is written, so a clash is detected up front: the run **pauses** and asks, rather than
silently renaming or replacing something. The dialog is a `Card` with the question, and three
buttons — *Overwrite* (primary), *Rename* and *Cancel* (both outline).

Only a **different** file already holding the name counts. A key already in the index is our own
earlier copy of the same file, reported as *Already saved*, so a repeat backup never asks.

The run resumes from exactly where it stopped — the backend keeps the selection, the position and
the decisions already made, so nothing ahead of the pause is re-downloaded. The queue shows the
waiting file in its own band, and *Cancel* skips that one file and lets the rest of the run
continue. Answering with an unknown value is rejected and the question stays open, and stopping the
run while it is waiting ends it cleanly rather than leaving a dialog with no way out.

## Settings

- The settings list starts directly below the top bar. It is a **two-column grid**
  (`minmax(0,1fr) 15rem`) with a single 240px control column: every select, input and button
  starts and ends on the same two edges whatever its intrinsic width, so a long label can never
  shift a control out of alignment. Below the `sm` breakpoint the columns collapse to one and the
  control goes full width, so nothing is ever clipped.
- Rows are grouped into three sections — **Backups**, **App**, **Setup** — separated by **24px** of
  space with **8px** between rows inside a section (the 2× ratio is what makes the grouping read as
  structure rather than noise; there are no divider lines). Each group has a small uppercase
  micro-heading. Every row carries a title, and a description wherever one helps, so no row is a bare
  label.
- The **access-token** field is forced `dir="ltr"` in every UI language: a token is always LTR, and
  without it the placeholder renders mirrored (`…figd`) and the reveal button lands on the text.
- The Donate card sits below the list at 24px, and the muted version line is the **last** element on
  the screen — not stranded between the list and the card.
- **One inset for the whole screen.** Group headings, row content and the Donate card all use the
  same 12px inline padding, so their *text* lands on one edge even though the card also has a ring
  on the outer column edge. Matching the box is not enough — a card padded 16px next to rows padded
  12px reads as a different width even when both are exactly 664px wide.
- **Backup location** — a short explanation of where single files land versus folder/team backups,
  the resolved absolute path from `bootstrap().downloads` (monospace, selectable, so it can be
  copied into a bug report), and an *Open Downloads* button. This is the only place the answer to
  "where did my files go?" is given; the per-row *Show in folder* only exists after a run.
- **Language** — English (default) / فارسی. Applies immediately, including direction.
- **Appearance** — Light / Dark / Follow system.
- **Access token** — replacing it reopens all three setup checks, since the saved browser session
  must still match the new token's access.
- **Redo setup** — re-run all three checks; a saved token can be reverified without re-entering it.
- A muted version line (`Fig Backup <version> · <platform>`, from `bootstrap().version`) closes the
  screen, below the donate card.

## Design system

| Token | Light | Dark | Source |
| --- | --- | --- | --- |
| Background / surfaces | `#ffffff` / `#f5f5f5` | `#2c2c2c` / `#383838` | `--figma-color-bg*` |
| Text / secondary | `rgba(0,0,0,.9)` / contrast-adjusted secondary | `#fff` / `.7` | `--figma-color-text*` via `src/index.css` |
| Brand (primary) | contrast-adjusted `#0d99ff` | contrast-adjusted `#0c8ce9` | `--figma-color-bg-brand` via `src/index.css` |
| Border | `#e6e6e6` | `#444444` | `--figma-color-border` |
| Success / Danger (text) | contrast-adjusted Figma colors | `#79d297` / `#fca397` | `--figma-color-text-success/-danger` via `src/index.css` |

- **Type**: Inter (fallback Helvetica). Size ramp from Tailwind defaults; titles use
  `text-2xl font-bold tracking-tight`, list rows `text-sm font-medium`, meta text `text-xs`.
- **Shape (nova)**: buttons h-28/h-24 rounded-lg without shadows, focus `ring-[3px]` at 50%
  brand, cards `rounded-lg ring-1` without borders/shadows, badges are pills, and progress rings
  use a 3px stroke.
- **Icons**: lucide only, one stroke weight, sized 14–16px; decorative icons are `aria-hidden`.
- **Motion**: 150ms color feedback, `active:translate-y-px` on buttons and progress-ring updates;
  spinners and ring transitions respect `prefers-reduced-motion`.
- **Fly-to-queue** (row download feedback): clicking a row's Download/Back up control flies a
  clone of the row's tile into the Downloads trigger — 400ms, `cubic-bezier(0.3, 0, 0.2, 1)`,
  scale 1 → 0.5, opacity fades in the last 35%; the trigger icon bumps 1.06× for 180ms on arrival
  (skipped while the manager is open). Reduced motion: 150ms accent tick + a polite live-region
  announcement instead.

## Internationalization (i18n)

- All copy lives in `src/i18n.js` + `src/i18n-languages-{a,b}.js` — nine languages matching
  Figma's list: English, فارسی (RTL), 日本語, Français, Deutsch, Español (España),
  Español (Latinoamérica), 한국어, Português (Brasil). `translate(lang, key, values)`
  interpolates `{placeholders}` and falls back to English. Add new strings to **all nine**
  languages (the language list itself lives in the exported `LANGUAGES` meta).
- Direction: `<html dir>` flips to `rtl` for Persian. Layout uses logical utilities
  (`ms-*`, `pe-*`, `start/end`); chevrons mirror via `rtl:-scale-x-100`; the progress fill and
  the select checkmark are repositioned by two CSS patches in `index.css`.
- Persian text in mixed rows is wrapped in `<bdi>` to keep bidi isolation.

## Accessibility notes (implemented)

- Selection controls are real `role="checkbox"` buttons: select-all reports
  `aria-checked="mixed"`, row checkboxes announce their label (“Select Marketing”).
- Icon-only buttons (back, download manager, settings, clear, close) carry `aria-label`s.
- Visible `focus-visible` rings on every interactive control; Esc exits select mode or closes the download manager and restores focus.
- Selection counts and run status updates are announced via `role="status"`; errors use
  `role="alert"`.
- **The error banner** is the app's single explanation surface. It carries a **localized
  headline** (what went wrong), a **localized hint** (what to do), a **Retry** button, and a
  close button. Raw backend wording is never shown inline — it sits behind a *Technical details*
  disclosure, so the user has something concrete to paste into a bug report without the banner
  ever opening with library internals. Classification lives in `src/api-errors.js` (pure, unit
  tested): *network* → “Couldn’t reach Figma” + the connection hint, *access* → “Figma denied the
  request” (a 401 gets its own token headline) + the permissions hint, *rate* → “Too many
  requests”, and anything unrecognized is shown verbatim with no redundant detail block.
- **Retry replays the whole operation.** Every bridge call runs through `call(label, action)`,
  where `action` is self-contained — it fetches *and* applies the result — so re-running it
  repeats the operation rather than re-fetching data nobody reads. It covers browse, teams
  folders, the token, the three setup steps, preferences, and the initial bootstrap (which
  previously left the app with no way forward but a relaunch). It is deliberately absent for
  failures that are not a failed operation, such as a sign-in that simply has not happened yet.
- Status is never color-only: every queue state pairs an icon + text label with its tint.
- Interactive targets are ≥ 24px (checkbox buttons are 24px; row actions h-24+ with spacing).
- `prefers-reduced-motion` disables the spinner and slide transitions (opacity fades instead).

## Design history

Earlier explorations are kept for reference at the repo root (static, self-contained HTML):

- `ui-proposals.html` — the visual-language proposals that led to adopting shadcn/ui nova + Figma tokens.
- `layout-proposals.html` — the layout/steps explorations (two-pane, Finder-style three-pane, linear
  wizard) that led to the shipped single-column layout; includes the design-director review and the
  decisions that were rejected (sidebar, three-column picker).
