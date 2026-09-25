"""
Unit tests for CLAUDE.md multi-tier loading and project scanner
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from myclaude.core.memory import (
    load_claude_md,
    scan_and_generate_claude_md,
)


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cwd = Path(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_claude_md_empty(self):
        # In a blank directory without CLAUDE.md
        # Note: might load global ~/.claude/CLAUDE.md if user has one on machine
        content, paths = load_claude_md(self.cwd)
        # Verify it doesn't crash
        self.assertIsInstance(content, str)
        self.assertIsInstance(paths, list)

    def test_load_project_claude_md(self):
        claude_file = self.cwd / "CLAUDE.md"
        with open(claude_file, "w", encoding="utf-8") as f:
            f.write("# Custom Project Rules\n- Rule 1: Always write tests")

        content, paths = load_claude_md(self.cwd)
        self.assertIn("Always write tests", content)
        self.assertIn(claude_file, paths)

    def test_scan_and_generate_python_project(self):
        # Create fake python project files
        req = self.cwd / "requirements.txt"
        with open(req, "w", encoding="utf-8") as f:
            f.write("pytest>=7.0.0\nopenai>=1.0.0\n")
        (self.cwd / "tests").mkdir()

        generated = scan_and_generate_claude_md(self.cwd)
        self.assertIn("Python 3", generated)
        self.assertIn("pytest", generated)
        self.assertIn("edit_file", generated)

    def test_scan_and_generate_node_project(self):
        pkg = self.cwd / "package.json"
        with open(pkg, "w", encoding="utf-8") as f:
            f.write('{"name": "my-web-app", "scripts": {"build": "tsc", "test": "jest"}}')

        generated = scan_and_generate_claude_md(self.cwd)
        self.assertIn("my-web-app", generated)
        self.assertIn("npm test", generated)
        self.assertIn("npm run build", generated)


if __name__ == "__main__":
    unittest.main()
