# Contributing to MyClaude

Thanks for your interest in improving MyClaude! This document explains how to
set up the project, run tests, and submit changes.

## Development Setup

```bash
git clone https://github.com/007350/myclaude.git
cd myclaude
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Configure your model provider by copying `.env.example` to `.env` and filling in
your credentials, then run:

```bash
python main.py
```

## Running Tests

All changes must keep the test suite green:

```bash
python -m unittest discover -s tests -v
```

CI runs the same command on Python 3.11 / 3.12 / 3.13 for every push and pull
request.

## Submitting Changes

1. Fork the repository and create a topic branch:
   `git checkout -b feat/your-feature`.
2. Keep commits focused and use clear messages
   (`feat: ...`, `fix: ...`, `docs: ...`, `perf: ...`, `refactor: ...`).
3. Add or update tests for any behavior change.
4. Ensure `python -m unittest discover -s tests` passes locally.
5. Open a pull request against `master` and describe **what** changed and
   **why**.

## Coding Style

- Pure standard library where practical; keep third-party dependencies minimal.
- Type hints for public functions.
- Prefer small, well-named modules under `myclaude/`.
- Update `README.md` / `README.zh-CN.md` when user-facing behavior changes.

## Reporting Bugs

Open an issue using the bug report template and include your OS, Python version,
model provider, and the exact steps to reproduce.

---

# 参与贡献

欢迎为 MyClaude 贡献代码！核心规则：**改动必须让测试保持通过**
（`python -m unittest discover -s tests`），提交信息遵循
`feat/fix/docs/perf/refactor` 前缀，行为变更需附带测试。
