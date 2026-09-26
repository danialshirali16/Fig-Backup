# Changelog

All notable changes to Fig Backup are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

Releases are built and published automatically when a `vX.Y.Z` tag is pushed to `main`, so the
binaries for every version below match the tag exactly.

## [Unreleased]

Work in progress on the next release. Notable items already merged since `v0.3.0`:

- Frameless-window resizing on Windows is fixed. The native window handle arrives from pythonnet as
  a `System.IntPtr`, which does not convert to a Python `int`; pywebview always calls `.ToInt32()`,
  so resizing failed outright on Windows.
- A per-file `403` is now treated as a failure for that file instead of invalidating the whole
  browser session, so one restricted file no longer aborts a team-wide backup.
- The setup flow and the Chromium downloader were reworked. Setup now prefers an already-installed
  Chrome or Edge and only falls back to downloading Chromium (about 325 MB) when neither can run.

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

[Unreleased]: https://github.com/danialshirali16/Fig-Backup/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/danialshirali16/Fig-Backup/compare/v0.2.0...v0.3.0
[0.2.1-rc.1]: https://github.com/danialshirali16/Fig-Backup/compare/v0.2.0...v0.2.1-rc.1
[0.2.0]: https://github.com/danialshirali16/Fig-Backup/releases/tag/v0.2.0
