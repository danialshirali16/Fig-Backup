# UI Guide

Screens, flows, and rules of the Fig Backup interface. The implementation lives in
`src/App.jsx`; visual language is Tailwind v4 + shadcn/ui (nova) with Figma design tokens
(see [ARCHITECTURE.md](ARCHITECTURE.md) → Design system).

## Window & layout

- Window: 960×700 (min 640×520). The **content column is capped at 680px**, centered.
- Sticky top bar: “Fig Backup” with *Download manager* (download icon, opens a popover) and *Settings* (gear) on the trailing edge. On Settings, the bar contains only a Back icon and “Settings” title. On macOS it fills the transparent native titlebar; the traffic-light controls stay at the physical left, with extra clearance below 840px.
- No sidebar. Navigation is the **breadcrumb** — `Teams / <Team> / <Folder>…` — where *Teams* is
  always the root exit, plus a predictable Back chevron next to the page title.

## Setup wizard (first run, or Settings → Redo setup)

Shown when there is no stored token or setup was never completed. Two steps with a numbered rail
(done / current / upcoming).

| Step | Contents | Exits |
| --- | --- | --- |
| 1 · Access token | PAT input (`figd_…`), scopes hint, privacy note. *Save and continue* verifies via `/v1/me` and shows “Token verified for *name*”. While the one-time browser setup runs, a slim status card (spinner + “One-time setup” + indeterminate bar) sits under the privacy note. | → Step 2 |
| 2 · Browser sign-in | Explains the one-time Figma browser session. *Open sign-in window* becomes *I've signed in* after opening. While setup runs the button is disabled and labeled “Waiting for one-time setup…” above a full status block (badge, ~150 MB note, indeterminate bar); on failure it becomes *Retry setup* next to a danger block (`role="alert"`). | *I've signed in* → Teams · **I'll sign in later** → Teams (postponed; always enabled) |

### One-time browser setup

Chromium (~150 MB) is not bundled; the app auto-downloads it once at launch (`bootstrap` → proactive install). One shared phase model — `ready` renders nothing, `setting_up` renders a brand-tinted status block with an honest **indeterminate** bar (the installer's output is quantized, so no percentage is fabricated; the bar is `aria-hidden` and the block is a `role="status"` live region), `failed` renders the danger pair with *Retry setup* in place. Surfaces: wizard steps 1–2, a Teams banner (Refresh hidden while installing; the “No teams found” empty state is gated on readiness and replaced by “Finding your teams…”), and the download-manager header (spinner block temporarily replaces the determinate progress ring; a running queue item reads “Waiting for one-time setup…”; after success a 2.5 s “Browser ready” flash plus a toast fires). After ~5 minutes the body copy swaps once to a slower-network note. There is deliberately no cancel — quitting the app is the implicit, safe cancel (the installer is idempotent and self-heals on next launch).

- **Postponed sign-in**: the app works normally; if a backup run fails because of a missing
  browser session, the app routes back to step 2 (step 1 shown complete) and the queue offers
  *Retry & continue*.
- **Language is English by default**; change it in Settings (or the “Change in Settings” link on
  step 1). There is deliberately no language step in the wizard.
- **Redo setup** (Settings) re-opens the wizard at step 1 if no token is stored, otherwise at
  step 2.

## Teams

Borderless list of discovered teams (team avatar, name, chevron). Avatars discovered in the
Figma team switcher are stored locally for display in the app; teams without an available image show
their initial. *Refresh* re-scrapes the team switcher (hidden while the one-time browser setup is
installing — it cannot help). If the browser session is missing, a banner offers *Open sign-in
window* (same as wizard step 2). During browser setup a status banner takes that slot (“Downloading
the backup browser”, or its danger variant with *Retry setup* on failure); the list area shows
“Finding your teams…” instead of the empty state until setup settles.

Row click → Browse for that team. While the team switcher is being scraped (Refresh or first
launch), the list is replaced by skeleton rows.

## Browse (folders & files)

Header: Back chevron + page title (current folder/team), breadcrumb underneath. Actions on the
trailing edge depend on context:

| Context | Actions |
| --- | --- |
| Team root, not selecting | *Download all* (primary) + *Select* |
| Inside a folder, not selecting | *Download all* + *Select* |
| Select mode | tri-state **Select-all** checkbox + “N of M selected” + *Done* |

Content uses the same borderless, rounded row style as Teams. Folders appear first in alphabetical order, followed by files in
alphabetical order. There are no section headers or download-location note. While a team or folder
listing loads, seven skeleton rows (pulsing tile + two lines, `role="status"`) replace the list —
navigation happens instantly and the data fills in.

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
- The list is split into two counted sections: **In Progress** (queued, running, failed, stopped)
  and **Completed** (done). Each row: a 28px icon (the real Figma file icon for files; muted
  `Users`/`Folder` tile for teams/folders), the name, and a **status caption** underneath —
  “Queue” while queued; the live export stage while running, using the design's exact wording
  (*Opening file... → Downloading assets... → Bundling...*), with “Collecting files…” plus an
  elapsed m:ss counter during the scanning phase, and a “*done* of *total* files” suffix for
  folder/team items); the
  error text for failures; and the **file size** (or the file count for folder/team rows) once
  done.
- Trailing per-row actions: queued rows show **Cancel** (remove from queue) and **Download
  next** (play — runs that item first) on hover or keyboard focus; the running row shows a spinner
  that swaps to **Cancel** (stop after current) the same way; completed rows show **Show in folder**
  (reveals the file in Finder/Explorer) on hover; failed/stopped rows always show **Cancel**
  (dismiss the row) and **Retry** (`refresh-cw`), with their error caption in the danger color —
  the error state per the Figma source of truth. The **Clear** header button renders only while
  completed rows exist.

Items run **sequentially** (folders first, then files). Closing the popover never affects the run;
Esc closes it and returns focus to the control that opened it. The popover is non-modal, so the rest
of the app remains available while a backup runs.

## Settings

- The settings card starts directly below the top bar, with 4px top and bottom padding and no gap between rows. The last row has no bottom divider. Token storage notes are documented in the README rather than repeated in the screen.
- **Language** — English (default) / فارسی. Applies immediately, including direction.
- **Appearance** — Light / Dark / Follow system.
- **Access token** — replace without redoing setup.
- **Redo setup** — re-run the wizard (token step skipped if a token is stored).

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
- Status is never color-only: every queue state pairs an icon + text label with its tint.
- Interactive targets are ≥ 24px (checkbox buttons are 24px; row actions h-24+ with spacing).
- `prefers-reduced-motion` disables the spinner and slide transitions (opacity fades instead).

## Design history

Earlier explorations are kept for reference at the repo root (static, self-contained HTML):

- `ui-proposals.html` — the visual-language proposals that led to adopting shadcn/ui nova + Figma tokens.
- `layout-proposals.html` — the layout/steps explorations (two-pane, Finder-style three-pane, linear
  wizard) that led to the shipped single-column layout; includes the design-director review and the
  decisions that were rejected (sidebar, three-column picker).
