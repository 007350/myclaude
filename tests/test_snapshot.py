"""
Unit tests for SnapshotManager and Atomic Undo safety net
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from myclaude.core.snapshot import SnapshotManager
from myclaude.tools.file_ops import write_file, edit_file
from myclaude.core import default_snapshot_manager


class TestSnapshotManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cwd = Path(self.test_dir)
        self.sm = SnapshotManager()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_rollback_existing_file(self):
        file_path = self.cwd / "sample.py"
        original_code = "def hello():\n    return 'world'\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original_code)

        # Record snapshot before change
        self.sm.record_before_change(file_path, "修改 sample.py")

        # Make destructive change
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("def broken():\n    raise Exception('oops')\n")

        # Commit checkpoint
        ckpt = self.sm.commit_checkpoint("步 1: 修改 sample.py")
        self.assertIsNotNone(ckpt)

        # Rollback
        ok, msg, reverted = self.sm.rollback_latest()
        self.assertTrue(ok)
        self.assertEqual(len(reverted), 1)

        # Verify content restored
        with open(file_path, "r", encoding="utf-8") as f:
            restored = f.read()
        self.assertEqual(restored, original_code)

    def test_rollback_newly_created_file(self):
        new_file = self.cwd / "created.py"
        self.assertFalse(new_file.exists())

        # Record snapshot before creation
        self.sm.record_before_change(new_file, "新建 created.py")

        # Create file
        with open(new_file, "w", encoding="utf-8") as f:
            f.write("print('brand new')\n")
        self.assertTrue(new_file.exists())

        # Commit and rollback
        self.sm.commit_checkpoint("步 1: 新建文件")
        ok, msg, reverted = self.sm.rollback_latest()
        self.assertTrue(ok)
        # Should be deleted
        self.assertFalse(new_file.exists())

    def test_multi_checkpoint_stack(self):
        f1 = self.cwd / "f1.txt"
        with open(f1, "w", encoding="utf-8") as f:
            f.write("v1")

        # Step 1: change to v2
        self.sm.record_before_change(f1, "v1 -> v2")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("v2")
        self.sm.commit_checkpoint("Step 1")

        # Step 2: change to v3
        self.sm.record_before_change(f1, "v2 -> v3")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("v3")
        self.sm.commit_checkpoint("Step 2")

        # First undo: should revert to v2
        ok, msg, reverted = self.sm.rollback_latest()
        self.assertTrue(ok)
        with open(f1, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "v2")

        # Second undo: should revert to v1
        ok, msg, reverted = self.sm.rollback_latest()
        self.assertTrue(ok)
        with open(f1, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "v1")

        # Third undo: stack is empty
        ok, msg, reverted = self.sm.rollback_latest()
        self.assertFalse(ok)
        self.assertEqual(len(reverted), 0)

    def test_tool_integration_write_and_edit_undo(self):
        default_snapshot_manager.clear()
        target = self.cwd / "tool_test.py"

        # 1. write_file creates file
        res = write_file(str(target), "def foo():\n    return 42\n")
        self.assertIn("成功写入", res)
        self.assertTrue(default_snapshot_manager.has_pending())
        default_snapshot_manager.commit_checkpoint("write_file")

        # 2. edit_file modifies file
        res2 = edit_file(str(target), "return 42", "return 100")
        self.assertIn("成功编辑", res2)
        default_snapshot_manager.commit_checkpoint("edit_file")

        # Check content is 100
        with open(target, "r", encoding="utf-8") as f:
            self.assertIn("return 100", f.read())

        # Rollback edit_file -> should be 42
        ok, msg, reverted = default_snapshot_manager.rollback_latest()
        self.assertTrue(ok)
        with open(target, "r", encoding="utf-8") as f:
            self.assertIn("return 42", f.read())

        # Rollback write_file -> file should be deleted
        ok, msg, reverted = default_snapshot_manager.rollback_latest()
        self.assertTrue(ok)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
