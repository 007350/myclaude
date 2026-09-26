# MyClaude — A Local Terminal AI Coding Agent in Pure Python

**English** | [简体中文](README.zh-CN.md)

[![Tests](https://github.com/007350/myclaude/actions/workflows/tests.yml/badge.svg)](https://github.com/007350/myclaude/actions/workflows/tests.yml)
[![GitHub stars](https://img.shields.io/github/stars/007350/myclaude?style=social)](https://github.com/007350/myclaude/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

A from-scratch, **pure-Python** autonomous coding agent for your terminal. It
runs a full ReAct loop — *think → call tools → execute → verify* — to search
code, read files in slices, apply precise edits, run tests, and self-heal
multi-round bugs.

Beyond raw coding, it ships production-grade architecture you can actually read
end-to-end: **two-tier context compaction**, **atomic shadow-snapshot rollback
(`/undo`)**, **`CLAUDE.md` project memory**, a **progressive-disclosure Skills
engine**, **MCP self-evolution**, and a **dual-track Sidecar companion
terminal**.

> Inspired by Claude Code. Built to be small, hackable, and dependency-light.

---

## 📸 Demo

<!--
  TODO: record a 20–30s terminal GIF and drop it at assets/demo.gif, then
  replace this comment block with:
  ![MyClaude demo](assets/demo.gif)
  Nothing sells a terminal agent like a moving picture — do this first.
-->

A short session (illustrative):

```text
👉 myclaude > fix the failing test in tests/test_editor.py and make sure the suite passes

🧠 thinking…
🔧 code_search("test_editor")            → 1 file
📖 read_file("tests/test_editor.py")     → lines 1-60
🔧 run_command("python -m unittest ...")  → 1 test failed
🔧 edit_file("myclaude/tools/editor.py", ...)  ✎ 5-tier match: fuzzy(0.94)
🔧 run_command("python -m unittest ...")  → OK (33 tests)
✅ done in 4 steps

👉 myclaude > /undo
⏪ restored 1 file, removed 0 — snapshot rolled back
```

---

## 🌟 Highlights

### 1. Core toolset with industrial-grade fault-tolerant editing
- **`edit_file` — a five-tier fallback match engine.** Instead of fragile
  full-file rewrites that burn tokens, it falls back gracefully:
  exact → CRLF/LF normalization → trailing-whitespace tolerance → indent
  re-alignment → **88% fuzzy similarity**.
- **`read_file`** sliced by line range, so long files never blow up the context.
- **`write_file`** auto-protected by the snapshot net before every write.
- **`code_search` / `find_files`** — ripgrep-like speed with built-in filtering
  of `.git`, `node_modules`, `venv`, and dozens of binary/skip patterns.
- **`run_command`** cross-platform (Windows PowerShell / Linux / macOS bash) with
  timeouts, head+tail truncation, and live streaming logs.

### 2. ⏪ Atomic safety net with instant rollback (`/undo`)
- **Shadow snapshots** capture the on-disk state before any write, committing
  each tool step as an atomic checkpoint.
- `/undo` restores instantly (and removes newly created files), then injects an
  "undo" event into agent memory so it doesn't loop on a dead-end idea.

### 3. 🗜️ Two-tier progressive context compaction
- **Tier 1 (soft trim):** collapses noisy early tool output (long logs, huge
  reads) — saving 50%+ of context.
- **Tier 2 (hard compaction):** an LLM micro-summary extracts *done / in-progress
  / pending* and preserves the static system-prompt prefix and recent turns.
- **KV-cache friendly:** tool schemas are deterministically sorted; the console
  shows live prompt-cache hit rate.

### 4. 🧠 Hierarchical project memory (`CLAUDE.md`)
- Merges global (`~/.claude/CLAUDE.md`) and project (`./CLAUDE.md`) rules.
- **`/init`** detects your stack (Python/Poetry/uv, Node/npm/pnpm/yarn/bun,
  Rust/Cargo, Go…) and scaffolds a rule file interactively.

### 5. 🤹 Progressive-disclosure Skills engine
- The system prompt ships only a tiny catalog (< 50 tokens).
- The agent auto-activates relevant skills via `activate_skill`, or you force
  one with `/skill <name>` — loading detailed guidance and bundled scripts on
  demand.

### 6. 🔌 MCP integration with runtime self-evolution
- Native **stdio MCP** support — mount browser automation, databases, APIs, etc.
- **`create_python_mcp_server`:** when the agent lacks a capability, it writes a
  FastMCP server itself and **hot-loads it with zero restart**.

### 7. 🛰️ Dual-track Sidecar companion terminal
- Run `python sidecar.py` in a second window beside the main agent.
- Watch live state, tool calls, timings and logs; steer with `/steer <note>`, or
  hard-stop a hung subprocess with `/interrupt`.

### 8. ⚡ YOLO mode with a permission guard
- **Safe (default):** blocks high-risk commands (destructive deletes, format,
  etc.) with `[y] once / [a] always (YOLO) / [n] deny`.
- **YOLO:** `/yolo` to auto-approve everything for full-speed autonomy.

---

## 🚀 Quickstart

```bash
git clone https://github.com/007350/myclaude.git
cd myclaude
pip install -r requirements.txt
python main.py
```

On first run, if no `.env` is found, an interactive wizard configures your
provider. It works with any OpenAI-compatible endpoint — **DeepSeek
(recommended)**, **OpenRouter**, local **Ollama**, and more.

Or copy `.env.example` to `.env` and fill it in:

```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
MAX_STEPS=30
```

---

## 🎮 Slash commands

| Command | Description |
| :--- | :--- |
| `/undo` | Instant atomic rollback of the last step's file changes, with memory sync |
| `/undo list` | List all rollback checkpoints in the undo stack |
| `/init` | Scan the repo, detect the stack, and scaffold `CLAUDE.md` |
| `/skills` | List all discovered global and project skills |
| `/skill <name>` | Explicitly activate a skill (e.g. `/skill git-workflow`) |
| `/compact` | Manually trigger deep context compaction (keeps KV-cache prefix) |
| `/yolo` or `/mode` | Toggle between YOLO and safe confirmation mode |
| `/mcp` or `/plugins` | List connected MCP servers and their tools |
| `/clear` or `/reset` | Clear context and reload `CLAUDE.md` + skills |
| `/model` or `/config` | Show the active model, base URL, and workspace |
| `/help` | Show detailed help |
| `/exit` or `/quit` | Gracefully shut down the MCP pool and exit |

---

## 🛰️ Sidecar companion terminal

Run a second window beside the main agent:

```bash
python sidecar.py
```

- **Live monitoring:** agent state transitions, current tool, timing, and logs.
- **Out-of-band steering:** `/steer <note>` injects guidance into the agent's next
  turn (e.g. `/steer read the existing tests before writing code`).
- **Emergency interrupt:** `/interrupt` kills a stuck subprocess immediately.

---

## 📂 Project structure

```text
myclaude/
├── main.py                     # Entry point
├── sidecar.py                  # Dual-track companion terminal
├── requirements.txt
├── myclaude/                   # Core package
│   ├── core/                   # state, context compaction, memory, skills, snapshot, parser
│   ├── mcp/                    # MCP stdio client & async session manager
│   ├── security/               # Permission guard (Normal / Strict / YOLO)
│   ├── tools/                  # editor, bash, file_ops, search, mcp_ops, skill_ops, registry
│   ├── ui/                     # Rich console rendering & prompt-cache stats
│   ├── agent.py                # ReAct reasoning loop
│   ├── cli.py                  # REPL & slash-command routing
│   └── config.py               # Env config & model params
├── skills/                     # Project-level skills (e.g. git-workflow)
├── custom_mcp_servers/         # Agent-generated local MCP servers
├── examples/                   # FastMCP server examples
├── docs/                       # Interactive architecture learning guide (GitHub Pages)
└── tests/                      # 33 unit tests
```

---

## 🧪 Testing

```bash
python -m unittest discover -s tests -v
```

CI runs the suite on Python 3.10 / 3.11 / 3.12 / 3.13.

---

## 📚 Interactive learning guide

An interactive walkthrough of the architecture — the 7-step ReAct pipeline,
module deep-dives, and a 5-dimension comparison with LangGraph state graphs:

- 🌐 **Online:** https://007350.github.io/myclaude/
- 📄 **Source:** [`docs/index.html`](docs/index.html)

---

## 🤝 Contributing

Issues and PRs are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). If
MyClaude is useful to you, a ⭐ helps others find it.

## 📄 License

[MIT](LICENSE) © 2026 zouxi
