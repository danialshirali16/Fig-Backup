# Agent instructions

## Use codebase-memory-mcp for architecture and impact analysis

This repository is indexed in the `codebase-memory-mcp` server under the project name
**`Fig-Backup-Mac`** (path `E:\Fig-Backup-Mac`). Before doing structural work, use it
instead of re-reading files ad hoc:

- **Architecture questions** (layers, boundaries, entry points, hotspots, clusters):
  `get_architecture` with the relevant `aspects` (`overview`, `structure`, `dependencies`,
  `boundaries`, `layers`, `hotspots`).
- **Before changing code — impact analysis**: run `detect_changes` (and `trace_path` with
  `direction: "inbound"`) on the functions you intend to touch to find callers and
  downstream consumers. Backend modules (`figma_backup/core.py`, `browser.py`, `app.py`)
  are high fan-in; check `tests/` usage via the `TESTS` edges too.
- **Finding code**: prefer `search_code` / `search_graph` over raw grep; use
  `query_graph` (Cypher) for multi-hop or cross-module questions
  (e.g. "who calls `_install_chromium`", "what writes `teams.json`").
- **After a structural change** (renames, moved modules, new modules, signature changes):
  re-index with `index_repository` (mode `moderate`) so the graph stays current, and use
  `compare_graphs` when you need a before/after diff of additions/removals.
- **Durable design decisions**: persist them as an ADR via `manage_adr`
  (e.g. the multi-source Chromium downloader, the Python segmented installer, the
  version fallback for Windows) instead of leaving them only in commit messages.

Known index caveats: `src/styles/style-nova.css` and parts of `src/index.css` are
best-effort parsed (CSS) — read those files directly when the graph answer looks
incomplete. Everything else (Python, JS, TS) is reliably indexed.
