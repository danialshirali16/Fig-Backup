# Changelog

All notable changes to Fig Backup are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

Releases are built and published automatically when a `vX.Y.Z` tag is pushed to `main`, so the
binaries for every version below match the tag exactly.

## [Unreleased]

Nothing yet.

## [1.0.0] — 2026-09-26

The first stable release. The Chromium downloader and the setup flow were reworked, file-name
conflicts are resolved by asking instead of silently renaming, and two platform bugs that broke
Windows resizing and large backups are fixed.

### Added

- **File-name conflict resolution.** When a *different* file already occupies the name a new one
  wants, the run pauses and asks whether to keep both or replace. Previously the app silently wrote
  `name (1).fig`. Re-downloading a file you already have is still recognised by its key and is not
  treated as a conflict.
- **Setup prefers a browser you already have.** An installed Chrome or Edge is used when one can
  run; Chromium is only downloaded (about 325 MB) when neither is available.
- **A downloader that survives a flaky network.** Chromium is fetched with Python range requests,
  falls back across mirror hosts, falls back to the pinned version when `--version` prints nothing,
  and uses the Playwright CLI only as a last resort.
- Breadcrumb navigation in the header, with file-type icons resolved on demand once a listing is on
  screen, so folders appear without waiting on a type lookup.

### Fixed

- **Frameless-window resizing on Windows.** The native window handle arrives from pythonnet as a
  `System.IntPtr`, which deliberately does not convert to a Python `int`; pywebview always calls
  `.ToInt32()`. Resizing the window failed outright.
- **A per-file `403` no longer kills the run.** It is now recorded as a failure for that file
  instead of invalidating the whole browser session, so one restricted file no longer aborts a
  team-wide backup.
- Right-to-left chrome in the setup flow, and the wizard card's framing and footer weighting.

### Changed

- Documentation: a [changelog](CHANGELOG.md), a code of conduct, a donate page, and a Documentation
  section in the README that finally links `docs/`.
- The repository now carries a social preview image, topics, and a corrected release-notes language
  list.

## [0.3.0] — 2026-09-25

### Added

- Redesigned Downloads manager: grouped *In Progress / Completed* sections, per-item
  **Retry / Cancel / Show in Folder**, hover actions, a mini progress bar in the app header, and a
  fly-to-queue animation when a download starts.
- Loading skeletons for teams, folders, and files, replacing silent waits while lists load.
- Breadcrumb navigation in the header, with file-type icons resolved on demand.
- All three Figma file types are backed up in their native formats: Design (`.fig`), FigJam (`.jam`),
  and Slides (`.deck`).
- The interface speaks 9 languages: English, فارسی, Deutsch, Español, Español (Latinoamérica),
  Français, Português (Brasil), 日本語, 한국어. The Vazirmatn font ships with the app for correct
  right-to-left rendering.

### Changed

- Upgraded to React 19 and Vite 8.

## [0.2.1-rc.1] — 2026-09-25

Pipeline validation build. Superseded by `v0.3.0` the same day.

## [0.2.0] — 2026-09-24

First public release.

### Added

- Native `.fig` backups from Figma, by automating the editor's *Save local copy* workflow through a
  locally installed Chromium.
- Two-step setup: access token, then a one-time browser sign-in.
- Multi-select backups — any mix of folders (recursive) and loose files, run as one sequential
  queue.
- Non-blocking download manager with live progress and per-item Retry / Stop / Cancel.
- Structure-preserving archives at `Downloads/Fig Backup/<Team>/<Folder>/…`, with collision-safe
  `name(1).fig` naming.
- Light, dark, and system themes, right-to-left layout support, and reduced-motion support.

[Unreleased]: https://github.com/danialshirali16/Fig-Backup/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/danialshirali16/Fig-Backup/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/danialshirali16/Fig-Backup/compare/v0.2.0...v0.3.0
[0.2.1-rc.1]: https://github.com/danialshirali16/Fig-Backup/compare/v0.2.0...v0.2.1-rc.1
[0.2.0]: https://github.com/danialshirali16/Fig-Backup/releases/tag/v0.2.0
