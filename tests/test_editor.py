"""
Unit tests for 5-tier fuzzy resilient code editor
"""
import unittest
from myclaude.tools.editor import apply_fuzzy_replace


class TestResilientEditor(unittest.TestCase):
    def setUp(self):
        self.code = (
            "def calculate(a, b):\n"
            "    # Add numbers together\n"
            "    result = a + b\n"
            "    return result\n"
        )

    def test_exact_match(self):
        success, new_code, method = apply_fuzzy_replace(
            self.code,
            old_str="    result = a + b",
            new_str="    result = a * b",
        )
        self.assertTrue(success)
        self.assertIn("Exact", method)
        self.assertIn("result = a * b", new_code)

    def test_line_trimmed_match(self):
        # Mismatched trailing spaces or leading indent
        success, new_code, method = apply_fuzzy_replace(
            self.code,
            old_str="# Add numbers together   \nresult = a + b",
            new_str="    # Multiply numbers together\n    result = a * b",
        )
        self.assertTrue(success)
        self.assertIn("result = a * b", new_code)

    def test_crlf_normalization(self):
        # Model sends \r\n while file has \n or vice versa
        success, new_code, method = apply_fuzzy_replace(
            self.code,
            old_str="def calculate(a, b):\r\n    # Add numbers together",
            new_str="def calculate(a, b, c=0):\n    # Add 3 numbers",
        )
        self.assertTrue(success)
        self.assertIn("def calculate(a, b, c=0):", new_code)

    def test_fuzzy_match(self):
        # Slightly altered comments or punctuation
        success, new_code, method = apply_fuzzy_replace(
            self.code,
            old_str="def calculate(a, b):\n    # Add numbers together!\n    result = a + b",
            new_str="def compute(a, b):\n    return a + b",
        )
        self.assertTrue(success)
        self.assertIn("def compute(a, b):", new_code)


if __name__ == "__main__":
    unittest.main()
