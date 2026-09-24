# Troubleshooting

Quick fixes for the most common problems. If yours isn't covered here, please
[open an issue](https://github.com/danialshirali16/Fig-Backup/issues) — and never paste your
Figma access token into an issue.

## macOS blocks the app (Gatekeeper)

Fig Backup is open source and unsigned, so macOS warns on first launch:

1. Right-click **Fig Backup.app** → **Open** → **Open** (only needed once).
2. Or: System Settings → Privacy & Security → find the warning → **Open Anyway**.
3. Terminal alternative: `xattr -dr com.apple.quarantine "/Applications/Fig Backup.app"`

## Windows: WebView2 or SmartScreen

- `Fig Backup.exe` needs the **WebView2 runtime** (preinstalled on Windows 10/11). If the window
  stays blank or errors about WebView2, install it from
  [Microsoft's WebView2 page](https://developer.microsoft.com/microsoft-edge/webview2/).
- SmartScreen may warn about the unsigned exe: choose **More info → Run anyway**.

## "One-time setup" / browser download fails

Chromium (~150 MB) is downloaded once, at first launch.

- Check your internet connection and press **Retry setup**.
- The installer is idempotent: quitting the app mid-download is safe, and the next launch continues
  where it left off.
- If it keeps failing, delete the downloaded browser cache — `~/Library/Caches/ms-playwright/` on
  macOS — and relaunch to force a clean re-download.

## Token problems

- **Verification fails / HTTP 401** — the token was revoked or mistyped. Create a new one
  (Figma → Settings → Security → Personal access tokens) and replace it under Settings → Access
  token.
- **Missing permissions** — the token needs `folders:read` and `file_metadata:read`; without them,
  teams or folders come back empty or forbidden. Older tokens with `projects:read` also work: the
  app falls back to the legacy Projects API automatically.
- **Where is it stored?** `~/Library/Application Support/Fig Backup/token.json` (permissions
  `0600`). A `FIGMA_PAT` environment variable, when set, overrides it at startup.

## Sign-in problems

- **"Sign-in required" before a backup** — the browser session expired, or you postponed sign-in
  during setup. Run *Settings → Redo setup* (the token step is skipped) or open the sign-in window
  again; after one sign-in, backups run headless with no visible browser.
- **"Editor blocked (HTTP 403)"** — Figma refused the automated editor session. Sign in again; if
  it repeats, wait a while before retrying.
- Backups stop on sign-in errors by design, since they cannot proceed without a session. Use
  **Retry & continue** in the download manager after signing back in.

## Backup behavior that looks like a bug

- **"Figma restricted this subfolder list" (HTTP 451)** — Figma doesn't expose subfolder listing
  for some regions/accounts. The backup still saves everything that *was* listed; the app warns
  that the result may be incomplete.
- **Files skipped as "Unsupported file type"** — Figma Design, FigJam, and Slides files are
  backed up (as `.fig`, `.jam`, and `.deck` native copies respectively); any other Figma editor
  type is skipped and listed with its type in the download manager.
- **"Already saved"** — the file already exists in the destination, so it wasn't downloaded again.
  Delete the old file to force a fresh copy.
- **Unexpected `name(1).fig` names** — name collisions in the destination are resolved by
  appending `(1)`, `(2)`, …
- **Figma rate limits (HTTP 429)** — the app retries automatically with backoff. If a run keeps
  failing on rate limits, back up fewer items at a time.
- **Corrupt downloads are rejected** — any response under 1 KB or that looks like an HTML/JSON
  error page is discarded instead of being saved as a `.fig`.

## Starting fresh

Quit the app, then delete any of these to reset parts of it:

- `~/Library/Application Support/Fig Backup/` — token, preferences, archive indexes
- `~/Library/Application Support/Figma Fig Downloader/` — browser profile and download index
  reused from the earlier shell tool
- `~/Library/Caches/ms-playwright/` — the downloaded Chromium

You'll need to re-enter the token and sign in again afterwards.

## Filing a backup failure

When a download fails, the app writes a debugging screenshot of the browser into its support
folder (`~/Library/Application Support/Fig Backup/`). Attach it (redacted as needed) to your
issue — it usually shows exactly what Figma displayed when the flow broke.
