# Security policy

## Supported versions

Only the latest [release](https://github.com/danialshirali16/Fig-Backup/releases) receives
security fixes.

## Reporting a vulnerability

Please report vulnerabilities **privately** via GitHub's *Report a vulnerability* flow
([Security → Advisories → New advisory](https://github.com/danialshirali16/Fig-Backup/security/advisories/new))
rather than opening a public issue. Include a description, reproduction steps, and the affected
version. You can expect an initial response within a few days, and fixes are released as soon as
practical.

## Design notes relevant to security

- Fig Backup is a local desktop app. It talks only to Figma (REST API + the web editor in a bundled
  Chromium) — no telemetry, no analytics, no update channel. Builds are published only through
  GitHub Releases.
- The Figma token is stored at `~/Library/Application Support/Fig Backup/token.json` with file
  permissions `0600` inside a `0700` folder. By design it is **not** stored in the system keychain
  and **not** separately encrypted — anyone with read access to your user account can read it. Do
  not use a shared macOS/Windows user account with Fig Backup.
- The bundled Chromium only automates the figma.com sign-in and *Save local copy* flow; it is not a
  general-purpose browser exposed to other sites.

Reports about the unencrypted token storage being a concern are welcome as discussion, but it is a
documented, deliberate trade-off rather than a vulnerability.
