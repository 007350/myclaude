import importlib
import pkgutil
import unittest

import myclaude


class TestPackageImports(unittest.TestCase):
    """Smoke test: every submodule must import without error.

    This catches missing imports / typos that break the app at startup but are
    invisible to unit tests that only exercise internals. (Regression guard for
    a missing `from .security import ...` in agent.py that made `python main.py`
    fail with NameError.)
    """

    def test_all_submodules_import(self):
        modules = [
            m.name
            for m in pkgutil.walk_packages(myclaude.__path__, prefix="myclaude.")
        ]
        self.assertTrue(modules, "no submodules discovered under myclaude")
        for name in modules:
            with self.subTest(module=name):
                importlib.import_module(name)

    def test_cli_entrypoint_imports(self):
        # main.py does `from myclaude.cli import main`
        importlib.import_module("myclaude.cli")


if __name__ == "__main__":
    unittest.main()
