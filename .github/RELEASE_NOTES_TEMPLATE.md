<!-- Template for GitHub release notes. Copy this into a new release, fill the placeholders,
     and delete this comment. "Generate release notes" categories come from .github/release.yml.

     Naming convention for assets:
       Fig-Backup-macOS.zip          (Release workflow, macOS Apple Silicon)
       Fig-Backup-Windows-x64.zip    (Release workflow, Windows x64)
       SHA256SUMS.txt                (Release workflow, SHA-256 of both zips)
-->

## Highlights

- …

## Downloads

| File | For |
| --- | --- |
| `Fig-Backup-macOS.zip` | macOS (Apple Silicon) |
| `Fig-Backup-Windows-x64.zip` | Windows 10/11 (x64) |

Verify integrity with `SHA256SUMS.txt`.

## Notes

- **macOS**: the build is unsigned — right-click the app → **Open** on first launch, or see
  [Troubleshooting](https://github.com/danialshirali16/Fig-Backup/blob/main/docs/TROUBLESHOOTING.md).
- **Windows**: requires the WebView2 runtime (preinstalled on Windows 10/11).
- Setup uses installed Chrome or Edge when available; otherwise it downloads Chromium once
  (~325 MB). Backups are saved locally.
