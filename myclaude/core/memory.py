import json
import os
from pathlib import Path
from typing import Tuple, List, Optional
from rich.prompt import Prompt


def get_global_claude_md_paths() -> List[Path]:
    """返回所有可能的全局 CLAUDE.md 探测路径"""
    home = Path.home()
    return [
        home / ".claude" / "CLAUDE.md",
        home / ".claude" / "claude.md",
        home / ".myclaude" / "CLAUDE.md",
        home / ".myclaude" / "claude.md",
        home / ".claude.md",
    ]


def get_project_claude_md_paths(cwd: Path) -> List[Path]:
    """返回当前项目所有可能的 CLAUDE.md 探测路径"""
    return [
        cwd / "CLAUDE.md",
        cwd / "claude.md",
        cwd / ".claude" / "CLAUDE.md",
        cwd / ".claude" / "claude.md",
        cwd / ".myclaude" / "CLAUDE.md",
        cwd / ".myclaude" / "claude.md",
    ]


def load_claude_md(cwd: Optional[Path] = None) -> Tuple[str, List[Path]]:
    """
    层级加载全局与项目级 CLAUDE.md 指令与规范
    返回: (合并后的指令文本, 已加载的文件路径列表)
    """
    if cwd is None:
        cwd = Path.cwd()

    loaded_paths: List[Path] = []
    global_content = ""
    project_content = ""

    # 1. 探测全局配置 (只取第一个存在的全局文件)
    for p in get_global_claude_md_paths():
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    global_content = f.read().strip()
                if global_content:
                    loaded_paths.append(p)
                    break
            except Exception:
                pass

    # 2. 探测项目级配置 (只取第一个存在的项目文件)
    for p in get_project_claude_md_paths(cwd):
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    project_content = f.read().strip()
                if project_content:
                    loaded_paths.append(p)
                    break
            except Exception:
                pass

    # 3. 合并逻辑
    if global_content and project_content:
        combined = (
            f"#### [全局用户偏好规范 (来自 ~/.claude/CLAUDE.md)]\n{global_content}\n\n"
            f"#### [当前项目专属架构规范 (来自 ./CLAUDE.md)]\n{project_content}"
        )
        return combined, loaded_paths
    elif project_content:
        return project_content, loaded_paths
    elif global_content:
        return global_content, loaded_paths

    return "", []


def scan_and_generate_claude_md(cwd: Path) -> str:
    """
    智能分析当前仓库环境与构建系统，自动生成高质量的 CLAUDE.md 初始规范
    """
    cwd = cwd.resolve()
    project_name = cwd.name or "项目"
    commands: List[str] = []
    conventions: List[str] = []
    tech_stack: List[str] = []

    # 1. Python 生态检测
    is_python = False
    pyproject = cwd / "pyproject.toml"
    req_file = cwd / "requirements.txt"
    setup_py = cwd / "setup.py"
    tests_dir = cwd / "tests"

    if pyproject.exists() or req_file.exists() or setup_py.exists():
        is_python = True
        tech_stack.append("Python 3")
        # 依赖安装
        if (cwd / "poetry.lock").exists():
            commands.append("- 安装依赖: `poetry install`")
            commands.append("- 运行测试: `poetry run pytest`")
        elif (cwd / "Pipfile").exists():
            commands.append("- 安装依赖: `pipenv install --dev`")
            commands.append("- 运行测试: `pipenv run pytest`")
        elif (cwd / "uv.lock").exists():
            commands.append("- 依赖同步: `uv sync`")
            commands.append("- 运行测试: `uv run pytest`")
        else:
            commands.append("- 安装依赖: `pip install -r requirements.txt`")
            if tests_dir.exists():
                commands.append("- 运行测试: `python -m unittest discover -s tests` 或 `pytest`")

        conventions.append("- 优先使用虚拟环境运行工具与测试")
        conventions.append("- 编辑已有代码前先用 read_file 确认已有逻辑，严格保持原有缩进与风格")

    # 2. Node.js / TypeScript 生态检测
    pkg_json = cwd / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            pkg_name = data.get("name")
            if pkg_name:
                project_name = pkg_name

            scripts = data.get("scripts", {})
            pkg_manager = "npm"
            if (cwd / "pnpm-lock.yaml").exists():
                pkg_manager = "pnpm"
            elif (cwd / "yarn.lock").exists():
                pkg_manager = "yarn"
            elif (cwd / "bun.lockb").exists():
                pkg_manager = "bun"

            tech_stack.append(f"Node.js ({pkg_manager})")
            if "build" in scripts:
                commands.append(f"- 项目构建: `{pkg_manager} run build`")
            if "test" in scripts:
                commands.append(f"- 单元测试: `{pkg_manager} test`")
            if "lint" in scripts:
                commands.append(f"- 代码检查: `{pkg_manager} run lint`")
            if "dev" in scripts:
                commands.append(f"- 开发服务: `{pkg_manager} run dev`")

            # 框架检测
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "typescript" in deps:
                tech_stack.append("TypeScript")
            if "react" in deps or "next" in deps:
                tech_stack.append("React")
            if "vue" in deps:
                tech_stack.append("Vue")
        except Exception:
            pass

    # 3. Rust 生态检测
    cargo_toml = cwd / "Cargo.toml"
    if cargo_toml.exists():
        tech_stack.append("Rust (Cargo)")
        commands.append("- 项目构建: `cargo build`")
        commands.append("- 单元测试: `cargo test`")
        commands.append("- 代码检查: `cargo clippy`")

    # 4. Go 生态检测
    go_mod = cwd / "go.mod"
    if go_mod.exists():
        tech_stack.append("Go")
        commands.append("- 单元测试: `go test ./...`")
        commands.append("- 项目构建: `go build`")

    # 默认兜底
    if not tech_stack:
        tech_stack.append("通用软件开发项目")
    if not commands:
        commands.append("- 单元测试: 根据具体模块使用对应的测试命令")
        commands.append("- 构建/校验: 请根据具体文件结构运行构建")

    commands_md = "\n".join(commands)
    conventions.append("- 修改代码遵循单一职责，避免引入冗余依赖")
    conventions.append("- 修改文件优先使用 edit_file 进行精准字符串替换，不要轻易全部重写")
    conventions_md = "\n".join(conventions)
    tech_str = ", ".join(tech_stack)

    content = f"""# {project_name} - 项目开发规范与智能体备忘录

## 核心技术栈 (Tech Stack)
- {tech_str}

## 常用命令 (Commands)
{commands_md}

## 代码风格与核心准则 (Code Style & Guidelines)
{conventions_md}

## 避坑指南与禁区 (Important Rules & Don'ts)
- 提交或反馈前务必使用 run_command 执行验证测试
- 涉及敏感配置（如 .env、密钥文件）禁止以明文打印或硬编码
- 任何破坏性文件删除或重写必须向用户二次确认
"""
    return content


def interactive_init_claude_md(cwd: Path, console) -> bool:
    """
    交互式初始化 CLAUDE.md：扫描项目、生成预览、提供微调确认并写入根目录
    """
    from ..ui import print_info, print_error
    from rich.panel import Panel
    from rich.syntax import Syntax

    target_file = cwd / "CLAUDE.md"
    if target_file.exists():
        console.print(f"[yellow]⚠️  检测到当前项目已存在 {target_file.name}。[/yellow]")
        overwrite = Prompt.ask("是否重新扫描并覆盖现有 CLAUDE.md?", choices=["y", "n"], default="n")
        if overwrite.lower() != "y":
            print_info("已取消初始化操作。")
            return False

    console.print("[dim]🔍 正在自动扫描代码库特征与构建工具配置...[/dim]")
    content = scan_and_generate_claude_md(cwd)

    # 打印代码高亮预览
    syntax = Syntax(content, "markdown", theme="monokai", line_numbers=True)
    console.print("\n")
    console.print(Panel(syntax, title="[bold green]📋 CLAUDE.md 自动生成草稿预览[/bold green]", border_style="cyan"))

    console.print("\n请选择操作:")
    console.print("  [1] 直接保存并生效 (Save directly)")
    console.print("  [2] 追加自定义项目说明/注意事项 (Append custom notes)")
    console.print("  [3] 取消放弃 (Cancel)")

    choice = Prompt.ask("请输入选项", choices=["1", "2", "3"], default="1")

    if choice == "3":
        print_info("已取消操作，未保存任何更改。")
        return False

    if choice == "2":
        extra_note = Prompt.ask("请输入你想追加的额外项目说明或规则 (例如：'所有接口必须遵循 RESTful 规范')")
        if extra_note.strip():
            content += f"\n## 用户自定义补充规范 (Custom Notes)\n- {extra_note.strip()}\n"

    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[bold green]✅ 成功生成并保存项目规范至: {target_file}[/bold green]")
        return True
    except Exception as e:
        print_error(f"写入 CLAUDE.md 失败: {str(e)}")
        return False
