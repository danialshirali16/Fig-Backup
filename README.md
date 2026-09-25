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
Apple Silicon Macs and Windows 10/11. It saves Figma Design files as `.fig`, FigJam files as
`.jam`, and Figma Slides as `.deck`.

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

On first launch, Fig Backup downloads Chromium (about 150 MB) to run the backup browser. The macOS
app is unsigned, so you may need to right-click it and choose **Open**. For installation help, see
[Troubleshooting](docs/TROUBLESHOOTING.md).

## Get started

1. Create a Figma Personal Access Token with `folders:read` and `file_metadata:read` permissions
   (older tokens with `projects:read` also work).
2. Open Fig Backup, paste the token, and sign in to Figma in the browser window it opens.
3. Choose a team. Select **Download all**, or use **Select** to pick specific folders and files.

Browser sign-in is required before the first backup; you can postpone it during setup and the app
will ask again when needed. After setup, backups run in the background.

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

## Help and contributing

Having trouble installing, signing in, or downloading? Read
[Troubleshooting](docs/TROUBLESHOOTING.md). Bug reports and contributions are welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md).

Fig Backup is an independent project and is not affiliated with Figma. It is released under the
[MIT License](LICENSE).

## Donate

If Fig Backup saves you time, support its development with Bitcoin:

<p align="center">
  <img src="docs/screenshots/donate-qr.png" alt="Bitcoin donation QR code" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>
