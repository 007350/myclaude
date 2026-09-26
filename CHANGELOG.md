# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-26

First public release of **MyClaude** — a local terminal AI coding agent written
in pure Python.

### Added

- **ReAct agent loop** with reasoning → tool call → execution → verification.
- **Five-tier fault-tolerant edit engine** (`edit_file`): exact match → CRLF/LF
  normalization → trailing-whitespace tolerance → indent re-alignment → 88%
  fuzzy similarity fallback.
- **Tool suite**: `read_file` (sliced reads), `write_file` (snapshot-protected),
  `code_search` / `find_files` (ripgrep-like, smart filtering), `run_command`
  (cross-platform, timeout + output truncation, streaming logs).
- **Atomic shadow-snapshot safety net** with `/undo` instant rollback and
  undo-aware memory injection.
- **Two-tier context compaction** (soft trim + LLM micro-summary) with KV-cache
  prefix preservation and live cache-hit stats.
- **`CLAUDE.md` hierarchical memory** with `/init` interactive scaffolding.
- **Progressive-disclosure Skills engine** (`/skill`, `activate_skill`).
- **MCP integration** with stdio transport and runtime self-evolution
  (`create_python_mcp_server`, hot reload without restart).
- **Dual-track Sidecar companion terminal** (`sidecar.py`) with live logs and
  out-of-band `/steer` / `/interrupt`.
- **YOLO fast mode** with a permission guard for high-risk commands.
- 33 unit tests covering compaction, editing, snapshots, parsing, package imports and more.

[Unreleased]: https://github.com/007350/myclaude/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/007350/myclaude/releases/tag/v0.1.0
