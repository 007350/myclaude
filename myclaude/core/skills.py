import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class Skill:
    name: str
    description: str
    triggers: List[str]
    dir_path: Path
    file_path: Path
    scripts_dir: Optional[Path] = None
    scripts: List[str] = field(default_factory=list)
    is_global: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "path": str(self.file_path),
            "scripts": self.scripts,
            "is_global": self.is_global,
        }


def parse_skill_markdown(file_path: Path, is_global: bool = False) -> Optional[Skill]:
    """解析单个 SKILL.md 文件的 YAML Frontmatter 及关联脚本"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    # 提取 YAML Frontmatter
    name = file_path.parent.name
    description = "无描述"
    triggers = []

    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        if yaml:
            try:
                parsed_fm = yaml.safe_load(fm_text) or {}
                if isinstance(parsed_fm, dict):
                    name = str(parsed_fm.get("name", name)).strip()
                    description = str(parsed_fm.get("description", description)).strip()
                    raw_triggers = parsed_fm.get("triggers", [])
                    if isinstance(raw_triggers, list):
                        triggers = [str(t).strip() for t in raw_triggers if t]
                    elif isinstance(raw_triggers, str):
                        triggers = [t.strip() for t in raw_triggers.split(",") if t.strip()]
            except Exception:
                pass
        else:
            # 简易正则备选
            name_m = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
            if name_m:
                name = name_m.group(1).strip()
            desc_m = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)
            if desc_m:
                description = desc_m.group(1).strip()
            trig_m = re.search(r"^triggers:\s*\[?(.*?)\]?$", fm_text, re.MULTILINE)
            if trig_m:
                triggers = [t.strip().strip("'\"") for t in trig_m.group(1).split(",") if t.strip()]

    # 检查关联的 scripts 目录
    scripts_dir = file_path.parent / "scripts"
    scripts_list = []
    if scripts_dir.is_dir():
        for item in scripts_dir.iterdir():
            if item.is_file() and not item.name.startswith("."):
                scripts_list.append(item.name)

    return Skill(
        name=name,
        description=description,
        triggers=triggers,
        dir_path=file_path.parent,
        file_path=file_path,
        scripts_dir=scripts_dir if scripts_dir.is_dir() else None,
        scripts=scripts_list,
        is_global=is_global,
    )


class SkillManager:
    """
    可插拔专业技能库管理器 (Skills Engine)
    - 采用渐进式披露 (Progressive Disclosure) 架构
    - 系统提示词仅注入极简清单 (Catalog)，消耗 < 50 Token
    - 运行时支持 Agent 自主按需激活 (activate_skill) 或用户命令 (/skill) 强注入
    """

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self._skills_cache: Dict[str, Skill] = {}
        self.scan_skills()

    def get_skill_search_dirs(self) -> List[Tuple[Path, bool]]:
        """获取所有技能搜索目录：(目录路径, 是否为全局)"""
        home = Path.home()
        dirs: List[Tuple[Path, bool]] = [
            (home / ".claude" / "skills", True),
            (home / ".myclaude" / "skills", True),
            (self.cwd / ".claude" / "skills", False),
            (self.cwd / ".myclaude" / "skills", False),
            (self.cwd / "skills", False),
        ]
        return dirs

    def scan_skills(self) -> Dict[str, Skill]:
        """全量扫描并刷新可用技能"""
        skills: Dict[str, Skill] = {}

        for search_dir, is_global in self.get_skill_search_dirs():
            if not search_dir.is_dir():
                continue
            for item in search_dir.iterdir():
                if not item.is_dir():
                    continue
                # 寻找 SKILL.md 或 skill.md
                skill_file = None
                for fname in ["SKILL.md", "skill.md"]:
                    candidate = item / fname
                    if candidate.is_file():
                        skill_file = candidate
                        break

                if skill_file:
                    skill = parse_skill_markdown(skill_file, is_global=is_global)
                    if skill:
                        # 项目级技能会覆盖同名全局技能
                        skills[skill.name] = skill

        self._skills_cache = skills
        return skills

    def list_skills(self) -> List[Skill]:
        """获取当前所有生效的技能列表"""
        return list(self._skills_cache.values())

    def get_skill(self, name: str) -> Optional[Skill]:
        """按技能名检索技能"""
        if name in self._skills_cache:
            return self._skills_cache[name]
        # 宽松查找 (小写或短横线匹配)
        name_clean = name.strip().lower().replace("_", "-")
        for k, v in self._skills_cache.items():
            if k.lower().replace("_", "-") == name_clean:
                return v
        return None

    def get_catalog_prompt(self) -> str:
        """
        生成注入 System Prompt 的极轻量技能清单 (渐进式披露)
        """
        skills = self.list_skills()
        if not skills:
            return ""

        lines = [
            "### 可用扩展技能库 (Skills - 按需查阅，绝不盲目全量加载):",
            "当用户任务涉及特定专业领域时，你有权通过 `activate_skill(skill_name=\"...\")` 工具按需载入其详尽操作指南与配套脚本，切勿臆测流程：",
        ]
        for s in skills:
            scope = "全局" if s.is_global else "项目"
            trig_str = f" (触发词: {', '.join(s.triggers)})" if s.triggers else ""
            lines.append(f"- **{s.name}** [{scope}]: {s.description}{trig_str}")

        return "\n".join(lines)

    def activate_skill(self, name: str) -> Tuple[bool, str]:
        """
        激活技能：读取其完整操作指令并汇报可用脚本
        返回: (成功: bool, 格式化后的详细指令: str)
        """
        skill = self.get_skill(name)
        if not skill:
            available = ", ".join([s.name for s in self.list_skills()]) or "无"
            return False, f"未找到名为 '{name}' 的技能。当前可用技能: [{available}]"

        try:
            with open(skill.file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_content = f.read()

            # 去除头部 YAML Frontmatter，直接呈现主体指令
            body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", raw_content, flags=re.DOTALL).strip()

            script_info = ""
            if skill.scripts and skill.scripts_dir:
                script_info = "\n\n#### 配套自动化脚本 (可使用 run_command 执行):\n"
                for script in skill.scripts:
                    full_p = skill.scripts_dir / script
                    script_info += f"- `{script}`: 绝对路径 `{full_p}`\n"

            formatted = (
                f"### [已激活专业技能: {skill.name}]\n"
                f"**简介**: {skill.description}\n"
                f"**指南来源**: `{skill.file_path}`\n\n"
                f"#### 操作与规范要求:\n"
                f"{body}"
                f"{script_info}"
            )
            return True, formatted
        except Exception as e:
            return False, f"激活技能 '{name}' 失败: {str(e)}"

    def scaffold_skill(self, name: str, is_global: bool = False) -> Path:
        """为用户脚手架式创建一个新技能模板"""
        clean_name = name.strip().lower().replace(" ", "-")
        if is_global:
            target_dir = Path.home() / ".myclaude" / "skills" / clean_name
        else:
            target_dir = self.cwd / ".myclaude" / "skills" / clean_name

        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "scripts").mkdir(exist_ok=True)

        skill_md = target_dir / "SKILL.md"
        template = f"""---
name: {clean_name}
description: 此处简要描述该技能的职责和解决的问题
triggers: ["{clean_name}", "example"]
---

### {clean_name} 操作指引与专业规范:
1. 步骤一: ...
2. 步骤二: ...

### 注意事项:
- 优先验证...
"""
        with open(skill_md, "w", encoding="utf-8") as f:
            f.write(template)

        self.scan_skills()
        return target_dir


default_skill_manager = SkillManager()
