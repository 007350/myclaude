"""
Unit tests for SkillManager, YAML frontmatter parsing, and progressive disclosure
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from myclaude.core.skills import SkillManager, parse_skill_markdown
from myclaude.tools import registry


class TestSkills(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cwd = Path(self.test_dir)

        # Create a mock project skill
        skill_dir = self.cwd / "skills" / "docker-flow"
        skill_dir.mkdir(parents=True)
        (skill_dir / "scripts").mkdir()

        self.skill_file = skill_dir / "SKILL.md"
        with open(self.skill_file, "w", encoding="utf-8") as f:
            f.write(
                "---\n"
                "name: docker-flow\n"
                "description: Docker 容器化构建与 Compose 部署指南\n"
                "triggers: [docker, compose, container]\n"
                "---\n\n"
                "### Docker 规范指南:\n"
                "1. 构建镜像使用多阶段构建减小体积。\n"
                "2. 禁止在镜像内硬编码密码。\n"
            )

        # Add a mock script
        script_file = skill_dir / "scripts" / "build_image.py"
        with open(script_file, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python\nprint('building docker image')\n")

        self.sm = SkillManager(cwd=self.cwd)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_parse_skill_markdown(self):
        skill = parse_skill_markdown(self.skill_file, is_global=False)
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, "docker-flow")
        self.assertEqual(skill.description, "Docker 容器化构建与 Compose 部署指南")
        self.assertIn("docker", skill.triggers)
        self.assertIn("build_image.py", skill.scripts)

    def test_scan_and_catalog(self):
        skills = self.sm.list_skills()
        skill_names = [s.name for s in skills]
        self.assertIn("docker-flow", skill_names)

        catalog = self.sm.get_catalog_prompt()
        self.assertIn("docker-flow", catalog)
        self.assertIn("Docker 容器化构建", catalog)
        self.assertIn("activate_skill", catalog)

    def test_activate_skill(self):
        ok, content = self.sm.activate_skill("docker-flow")
        self.assertTrue(ok)
        self.assertIn("多阶段构建", content)
        self.assertIn("build_image.py", content)

    def test_activate_nonexistent_skill(self):
        ok, content = self.sm.activate_skill("unknown-magic-skill")
        self.assertFalse(ok)
        self.assertIn("未找到", content)

    def test_tool_registry_has_activate_skill(self):
        schemas = registry.get_schemas()
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertIn("activate_skill", tool_names)


if __name__ == "__main__":
    unittest.main()
