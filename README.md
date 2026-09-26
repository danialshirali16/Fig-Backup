<p align="center">
  <img src="docs/screenshots/icon-256.png" width="88" alt="Fig Backup icon">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <b>English</b> · <a href="docs/readme/README.fa.md">فارسی</a> · <a href="docs/readme/README.ar.md">العربية</a> · <a href="docs/readme/README.de.md">Deutsch</a> · <a href="docs/readme/README.es.md">Español</a> · <a href="docs/readme/README.fr.md">Français</a> · <a href="docs/readme/README.pt-BR.md">Português</a> · <a href="docs/readme/README.ru.md">Русский</a> · <a href="docs/readme/README.tr.md">Türkçe</a> · <a href="docs/readme/README.zh-CN.md">中文</a> · <a href="docs/readme/README.ja.md">日本語</a>
  <!-- Add one link per translated README -->
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/ci.yml"><img alt="CI status" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/ci.yml/badge.svg"></a>
</p>

**Save native copies of your Figma files to your computer.** Fig Backup is a free desktop app for
Apple Silicon Macs (macOS 12 or later) and Windows 10/11. It saves Figma Design files as `.fig`,
FigJam files as `.jam`, and Figma Slides as `.deck`. The interface speaks 9 languages, including
right-to-left layouts for فارسی.

<p align="center">
  <img src="docs/screenshots/cover.png" alt="Fig Backup cover — native .fig backups from Figma, free local desktop app for macOS and Windows" width="100%">
</p>

## Download

Get the [**latest release**](https://github.com/danialshirali16/Fig-Backup/releases/latest):

| Platform | Download |
| --- | --- |
| macOS (Apple Silicon) | [Click here](https://github.com/danialshirali16/Fig-Backup/releases/latest) |
| Windows 10/11 (x64) | [Click here](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip) |

Every release also ships a `SHA256SUMS.txt` with checksums for both files.

Fig Backup uses Chrome or Edge already installed on your computer when available. If neither can
run, it downloads Chromium and its headless build (about 325 MB total). The macOS
app is unsigned, so you may need to right-click it and choose **Open**. For installation help, see
[Troubleshooting](docs/TROUBLESHOOTING.md).

## Get started

1. In Figma, open your account menu → **Settings** → **Security** → **Personal access tokens** →
   **Generate new token**. Name it Fig Backup and enable `folders:read`, `file_metadata:read`, and
   `current_user:read`. Copy the token immediately; Figma shows it only once. Older tokens with
   `projects:read` can still use the legacy folder API.
2. Open Fig Backup. Setup checks Chrome or Edge first and downloads Chromium only if needed. Verify the browser, paste and verify the token, then sign in to Figma and click **Verify sign-in**. The sign-in window closes; backups use a hidden browser.
3. Choose a team. Select **Download all**, or use **Select** to pick specific folders and files.

All three setup checks are required before the first backup. After setup, backups run in the background.

## What gets backed up?

- Figma Design, FigJam, and Slides files are saved in their native formats:<br>
  <img src="docs/screenshots/figma-file-design.png" height="20" alt="Figma Design files">
  <img src="docs/screenshots/figma-file-figjam.png" height="20" alt="FigJam files">
  <img src="docs/screenshots/figma-file-slides.png" height="20" alt="Figma Slides files">
- Back up a whole team with one click, or use **Select** to choose folders and individual files.
- Folder backups preserve the team and folder structure.
- The download manager shows live progress and lets you retry, stop, or cancel queued items.
  Unsupported file types are skipped and don't count toward the progress percent.

Team and folder backups go to `Downloads/Fig Backup/<Team>/<Folder>/…`. Individual files go
directly to `Downloads`. If a filename already exists, Fig Backup adds a number instead of
overwriting it.

## How it works

Figma's REST API does not provide native file exports. Fig Backup uses a browser to automate the
Figma editor's **Save local copy** action, so what lands on your disk is the same file the Figma
editor produces. Because this depends on Figma's web interface, a future Figma change may require
an app update.

## Screenshots

| Setup wizard | Folders & files |
| --- | --- |
| <img src="docs/screenshots/setup-wizard.png" alt="Setup wizard — browser sign-in step"> | <img src="docs/screenshots/browse-light.png" alt="Browsing a team's folders and files"> |
| **Download manager** | **Dark mode** |
| <img src="docs/screenshots/download-manager.png" alt="Download manager popover with a running queue"> | <img src="docs/screenshots/dark-mode.png" alt="Browse view with the dark theme"> |

## Privacy and security

Backups are saved on your computer. Fig Backup communicates with Figma to access your files and
does not upload your files or token to a Fig Backup server, and there is no telemetry.

Your token is stored at `~/Library/Application Support/Fig Backup/token.json` with file
permissions `0600`. It is not stored in the system keychain and not separately encrypted — do not
use a shared computer account. A `FIGMA_PAT` environment variable can override it for scripted
launches. See [SECURITY.md](SECURITY.md) for details. Use the app only with files you are
authorized to access.

## Documentation

| | |
| --- | --- |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Gatekeeper, SmartScreen, WebView2, setup failures, HTTP 403/451 |
| [Changelog](CHANGELOG.md) | What changed in every release |
| [Architecture](docs/ARCHITECTURE.md) | How the backend, browser bridge, and interface fit together |
| [Interface guide](docs/UI.md) | Design tokens, component conventions, and accessibility rules |
| [Security](SECURITY.md) | How your token is stored and what the app does and does not send |
| [Contributing](CONTRIBUTING.md) | Development setup and conventions |
| [Code of Conduct](CODE_OF_CONDUCT.md) | What is expected of everyone taking part |

Looking for this page in another language? The README is translated into
[فارسی](docs/readme/README.fa.md) · [العربية](docs/readme/README.ar.md) ·
[Deutsch](docs/readme/README.de.md) · [Español](docs/readme/README.es.md) ·
[Français](docs/readme/README.fr.md) · [Português](docs/readme/README.pt-BR.md) ·
[Русский](docs/readme/README.ru.md) · [Türkçe](docs/readme/README.tr.md) ·
[中文](docs/readme/README.zh-CN.md) · [日本語](docs/readme/README.ja.md)

## Help and contributing

Having trouble installing, signing in, or downloading? Read
[Troubleshooting](docs/TROUBLESHOOTING.md).

Questions, ideas, and "is this supposed to happen?" — those belong in
[Discussions](https://github.com/danialshirali16/Fig-Backup/discussions), not in an issue. Bugs and
feature requests are welcome on the [issue tracker](https://github.com/danialshirali16/Fig-Backup/issues);
please read [the pinned issue](https://github.com/danialshirali16/Fig-Backup/issues/1) first, it
covers the most common reports. Contributions are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Legal

Fig Backup is an independent project. It is not affiliated with, endorsed by, or sponsored by
Figma, Inc. Fig, Figma, FigJam, Figma Slides, and the Figma logo are trademarks of Figma, Inc.; they
are used here only to describe what the app works with.

The app talks to Figma's REST API using a personal access token that **you** generate and own, under
[Figma's API terms](https://www.figma.com/developers/api#access-tokens). It also drives a local
browser you are already signed into, which is a best-effort integration: if Figma changes its web
interface, an app update may be needed. Use it only with files you are authorized to access.

Released under the [MIT License](LICENSE).

## Donate

Fig Backup is free, has no ads, no telemetry, and no paid tier. If it saves you time, you can
[support its development](docs/DONATE.md) with Bitcoin — or just star the repository, report a bug,
or translate this page into a language it is missing.
