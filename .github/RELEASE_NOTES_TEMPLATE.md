<!-- Template for GitHub release notes. Copy this into a new release, fill the placeholders,
     and delete this comment. "Generate release notes" categories come from .github/release.yml.

     Naming convention for assets:
       Fig-Backup-vX.Y.Z-macOS.zip    (./build-mac.sh, zip the .app with ditto)
       Fig-Backup-Windows-x64.zip    (Windows build CI artifact, windows-build branch)
       SHA256SUMS.txt                (shasum -a 256 over the zips)
-->

## Highlights

- …

## Downloads

| File | For |
| --- | --- |
| `Fig-Backup-vX.Y.Z-macOS.zip` | macOS (Apple Silicon) |
| `Fig-Backup-Windows-x64.zip` | Windows 10/11 (x64) |

Verify integrity with `SHA256SUMS.txt`.

## Notes

- **macOS**: the build is unsigned — right-click the app → **Open** on first launch, or see
  [Troubleshooting](https://github.com/danialshirali16/Fig-Backup/blob/main/docs/TROUBLESHOOTING.md).
- **Windows**: requires the WebView2 runtime (preinstalled on Windows 10/11).
- First launch downloads Chromium once (~150 MB); everything else runs locally.
