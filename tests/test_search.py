"""
Unit tests for code_search and find_files codebase exploration tools
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from myclaude.tools.search import code_search, find_files
from myclaude.core.parser import normalize_parameters
from myclaude.tools import registry


class TestSearchTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cwd = Path(self.test_dir)

        # Create subdirectories
        (self.cwd / "src").mkdir()
        (self.cwd / "node_modules" / "pkg").mkdir(parents=True)
        (self.cwd / "tests").mkdir()

        # Create code files
        with open(self.cwd / "src" / "auth.py", "w", encoding="utf-8") as f:
            f.write(
                "def authenticate_user(token: str):\n"
                "    # Verify token payload\n"
                "    return {'status': 'authenticated'}\n"
            )

        with open(self.cwd / "src" / "utils.py", "w", encoding="utf-8") as f:
            f.write(
                "def format_token(raw: str):\n"
                "    return f'Bearer {raw}'\n"
            )

        # File in ignored directory
        with open(self.cwd / "node_modules" / "pkg" / "dummy.py", "w", encoding="utf-8") as f:
            f.write("def authenticate_user(): pass\n")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_code_search_exact_match(self):
        res = code_search(query="authenticate_user", path=str(self.cwd))
        self.assertIn("找到 1 处匹配", res)
        self.assertIn("auth.py:1", res)
        # Ignored dir must NOT be searched
        self.assertNotIn("node_modules", res)

    def test_code_search_regex(self):
        res = code_search(query=r"def\s+\w+_user", path=str(self.cwd), is_regex=True)
        self.assertIn("找到 1 处匹配", res)
        self.assertIn("auth.py:1", res)

    def test_code_search_file_pattern_filter(self):
        res = code_search(query="token", path=str(self.cwd), file_pattern="*auth*")
        self.assertIn("auth.py", res)
        self.assertNotIn("utils.py", res)

    def test_find_files(self):
        res = find_files(pattern="*.py", path=str(self.cwd))
        self.assertIn("auth.py", res)
        self.assertIn("utils.py", res)
        self.assertNotIn("dummy.py", res)

    def test_search_parameter_alias_normalization(self):
        p1 = normalize_parameters("code_search", {"keyword": "foo", "dir": "src"})
        self.assertEqual(p1["query"], "foo")
        self.assertEqual(p1["path"], "src")

        p2 = normalize_parameters("find_files", {"file_pattern": "*.ts"})
        self.assertEqual(p2["pattern"], "*.ts")

    def test_tools_registered(self):
        names = [s["function"]["name"] for s in registry.get_schemas()]
        self.assertIn("code_search", names)
        self.assertIn("find_files", names)


if __name__ == "__main__":
    unittest.main()
