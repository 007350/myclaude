"""
Unit tests for JSON repair and parameter alias normalizer
"""
import unittest
from myclaude.core.parser import robust_json_parse, normalize_parameters


class TestParser(unittest.TestCase):
    def test_markdown_codeblock_stripping(self):
        raw = '```json\n{"path": "hello.py", "content": "print(1)"}\n```'
        ok, data, err = robust_json_parse(raw)
        self.assertTrue(ok)
        self.assertEqual(data["path"], "hello.py")

    def test_trailing_commas_and_unquoted_keys(self):
        raw = '{"path": "src/main.py", "content": "hello",}'
        ok, data, err = robust_json_parse(raw)
        self.assertTrue(ok)
        self.assertEqual(data["path"], "src/main.py")

    def test_single_quoted_json(self):
        raw = "{'command': 'git status', 'timeout': 30}"
        ok, data, err = robust_json_parse(raw)
        self.assertTrue(ok)
        self.assertEqual(data["command"], "git status")

    def test_parameter_alias_normalization(self):
        # file_path -> path
        norm1 = normalize_parameters("read_file", {"file_path": "a.txt"})
        self.assertEqual(norm1["path"], "a.txt")

        # cmd -> command
        norm2 = normalize_parameters("run_command", {"cmd": "ls -la"})
        self.assertEqual(norm2["command"], "ls -la")

        # target_file, search, replace -> edit_file
        norm3 = normalize_parameters(
            "edit_file",
            {"target_file": "b.py", "search": "old", "replace": "new"}
        )
        self.assertEqual(norm3["path"], "b.py")
        self.assertEqual(norm3["old_str"], "old")
        self.assertEqual(norm3["new_str"], "new")


if __name__ == "__main__":
    unittest.main()
