import sys
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Confirm
from typing import Dict, Any, Optional, List

# 保证 Windows 终端下 UTF-8 与 Emoji 正常渲染，防止 GBK 编码报错
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(legacy_windows=False)


def print_welcome(
    model_name: str,
    cwd: str,
    mcp_count: int = 0,
    sidecar_port: int = 0,
    claude_md_found: bool = False,
    skill_count: int = 0,
):
    text = Text()
    text.append("🤖 MyClaude Agent CLI\n", style="bold cyan")
    text.append(f"• 模型: {model_name}\n", style="green")
    text.append(f"• 工作区: {cwd}\n", style="yellow")
    if claude_md_found:
        text.append("• 规则规范: 已成功装载 CLAUDE.md 长期记忆\n", style="bold green")
    if skill_count > 0:
        text.append(f"• 扩展技能: 已发现 {skill_count} 个按需领域技能 (输入 /skills 查看)\n", style="bold cyan")
    if mcp_count > 0:
        text.append(f"• MCP 插件: 已挂载 ({mcp_count} 个外部工具)\n", style="bold magenta")
    if sidecar_port > 0:
        text.append(f"• 伴生窗口: 监听端口 {sidecar_port}（可在侧边终端运行 python sidecar.py 连通）\n", style="bold blue")
    text.append("• 输入具体任务，Agent 会自主思考、读取与编写代码、执行命令\n", style="dim")
    text.append("• 常用命令: /init (初始化规范), /skills (技能库), /yolo (极速放行), /compact (压缩), /mcp (插件)", style="dim italic")

    console.print(Panel(text, title="[bold magenta]Claude Code Python 本地版[/bold magenta]", border_style="cyan"))


def print_user_prompt():
    console.print()


def print_assistant_message(content: str):
    if not content:
        return
    console.print()
    console.print(Panel(Markdown(content), title="[bold green]Agent[/bold green]", border_style="green"))


def print_tool_call(name: str, args: Dict[str, Any]):
    """渲染工具调用卡片"""
    title = f"🛠️  调用工具: [bold yellow]{name}[/bold yellow]"
    
    # 特别针对命令和代码高亮展示
    if name == "run_command" and "command" in args:
        cmd_text = Syntax(args["command"], "powershell", theme="monokai", line_numbers=False)
        console.print(Panel(cmd_text, title=title, border_style="yellow"))
    elif name in ("write_file", "edit_file") and "path" in args:
        details = [f"[bold]目标文件:[/bold] {args['path']}"]
        if "old_str" in args:
            details.append(f"[dim]匹配长度: {len(args['old_str'])} 字符 | 新替换: {len(args.get('new_str', ''))} 字符[/dim]")
        elif "content" in args:
            details.append(f"[dim]内容大小: {len(args['content'])} 字符[/dim]")
        console.print(Panel("\n".join(details), title=title, border_style="yellow"))
    else:
        args_str = json.dumps(args, ensure_ascii=False, indent=2)
        console.print(Panel(Syntax(args_str, "json", theme="monokai"), title=title, border_style="yellow"))


def print_tool_result(name: str, result: str, max_lines: int = 15):
    """渲染工具执行结果卡片（只展示前几行预览，避免刷屏）"""
    lines = result.splitlines()
    if len(lines) > max_lines:
        preview = "\n".join(lines[:max_lines]) + f"\n... [剩余 {len(lines) - max_lines} 行已省略]"
    else:
        preview = result

    style = "red" if "错误" in result or "[退出码" in result else "blue"
    console.print(Panel(preview, title=f"📋 工具结果: {name}", border_style=style))


from rich.prompt import Confirm, Prompt


def ask_permission(action_desc: str) -> bool:
    """危险或敏感操作的交互式确认"""
    console.print(f"[bold red]⚠️ 权限拦截提示:[/bold red] Agent 请求执行高危或修改操作:\n  [yellow]{action_desc}[/yellow]")
    return Confirm.ask("是否允许继续执行？", default=True)


def ask_permission_choice(action_desc: str) -> str:
    """
    危险或敏感操作的交互式确认:
    [y] 允许单次执行
    [a] 始终允许（自动切换至 YOLO 模式）
    [n] 拒绝执行
    """
    console.print(f"\n[bold red]⚠️  权限拦截提示:[/bold red] Agent 请求执行: {action_desc}")
    choice = Prompt.ask(
        "  选择操作: [green][y]单次允许[/green] / [yellow][a]始终允许(YOLO)[/yellow] / [red][n]拒绝[/red]",
        choices=["y", "a", "n", "yes", "no"],
        default="y",
    ).lower()
    if choice in ("y", "yes"):
        return "y"
    elif choice == "a":
        return "a"
    return "n"


def print_yolo_status(is_yolo: bool):
    if is_yolo:
        console.print("[bold yellow]⚡ 已开启 YOLO 模式: 所有终端命令与文件操作将全自动放行！[/bold yellow]")
    else:
        console.print("[bold green]🛡️  已切回安全模式: 遇到高危终端命令将主动拦截确认。[/bold green]")


def print_error(msg: str):
    console.print(f"[bold red]❌ 错误:[/bold red] {msg}")


def print_info(msg: str):
    console.print(f"[bold cyan]ℹ️ 信息:[/bold cyan] {msg}")


def print_mcp_servers(stats: Dict[str, List[str]]):
    """展示已挂载的 MCP 服务及其工具"""
    if not stats:
        console.print("[dim]当前未挂载任何 MCP 服务。可在项目根目录创建 mcp.json 配置服务，参考 mcp.json.example。[/dim]")
        return

    from rich.table import Table
    table = Table(title="🔌 已挂载的 MCP 服务与工具", border_style="cyan")
    table.add_column("MCP 服务名", style="bold green", justify="left")
    table.add_column("工具数量", style="yellow", justify="center")
    table.add_column("包含工具清单", style="white", justify="left")

    for s_name, tools in stats.items():
        table.add_row(s_name, str(len(tools)), ", ".join(tools))

    console.print(table)


def print_cache_stats(hit_tokens: int, total_tokens: int, ratio: float):
    """展示当前轮次的 Prompt 缓存命中情况"""
    console.print(
        f"[dim]⚡ [cyan]Prompt 缓存命中:[/cyan] [bold green]{ratio}%[/bold green] "
        f"({hit_tokens}/{total_tokens} tokens 复用 KV Cache)[/dim]"
    )


def print_compaction_card(stats: Dict[str, Any]):
    """展示上下文窗口瘦身卡片"""
    is_hard = stats.get("compressed", False)
    title = "🗜️  上下文深度微摘要压缩已触发" if is_hard else "✂️  历史工具输出自动折叠裁剪"
    style = "magenta" if is_hard else "yellow"

    before = stats.get("before_tokens", 0)
    after = stats.get("after_tokens", 0)
    saved = stats.get("saved_tokens", 0)
    ratio = stats.get("ratio", 0)

    desc = [
        f"[bold]压缩前消耗:[/bold] {before:,} tokens  ─►  [bold green]压缩后占用:[/bold green] {after:,} tokens",
        f"[bold cyan]释放上下文空间:[/bold cyan] {saved:,} tokens ([bold green]节省 {ratio}%[/bold green])",
    ]
    if is_hard:
        desc.append("[dim]已自动浓缩前期已完成事项与修改记录，核心执行状态无损保留。[/dim]")

    console.print(Panel("\n".join(desc), title=f"[bold {style}]{title}[/bold {style}]", border_style=style))


def print_skills_table(skills: List[Any]):
    """以表格形式展示已发现的扩展技能库"""
    if not skills:
        console.print("[dim]当前未发现任何扩展技能 (Skills)。可在项目根目录或 ~/.myclaude/skills 创建技能文件夹。[/dim]")
        return

    from rich.table import Table
    table = Table(title="🤹 已发现的领域扩展技能 (Skills)", border_style="cyan")
    table.add_column("技能名 (Name)", style="bold cyan", justify="left")
    table.add_column("作用域", style="yellow", justify="center")
    table.add_column("触发关键词 (Triggers)", style="magenta", justify="left")
    table.add_column("脚本数", style="green", justify="center")
    table.add_column("技能职责与描述", style="white", justify="left")

    for s in skills:
        scope = "全局 [~/.myclaude]" if getattr(s, "is_global", False) else "项目 [./skills]"
        trig = ", ".join(getattr(s, "triggers", [])) or "-"
        scripts_count = str(len(getattr(s, "scripts", [])))
        table.add_row(
            getattr(s, "name", "unknown"),
            scope,
            trig,
            scripts_count,
            getattr(s, "description", "")
        )

    console.print(table)


def print_skill_activation(skill_name: str, detail: str):
    """展示技能激活详情面板"""
    console.print(Panel(Markdown(detail), title=f"[bold magenta]⚡ 技能已激活: {skill_name}[/bold magenta]", border_style="magenta"))


def print_undo_card(message: str, reverted_files: List[Any]):
    """展示原子回滚成功卡片"""
    from pathlib import Path
    lines = [f"[bold green]{message}[/bold green]"]
    if reverted_files:
        lines.append("\n[bold cyan]已精准恢复的文件清单:[/bold cyan]")
        for f in reverted_files:
            lines.append(f"  • [yellow]{Path(f).name}[/yellow] ([dim]{f}[/dim])")
    lines.append("\n[dim]💡 提示: Agent 认知记忆已同步注入该回滚事件，防止在错误路线上反复死磕。[/dim]")
    console.print(Panel("\n".join(lines), title="[bold green]⏪ 原子版本回滚成功 (Atomic Undo)[/bold green]", border_style="green"))


def print_undo_stack(stack: List[Dict[str, Any]]):
    """展示当前可回滚的历史检查点栈"""
    if not stack:
        console.print("[dim]当前 Undo 栈为空，没有任何可回滚的文件修改记录。[/dim]")
        return

    from rich.table import Table
    table = Table(title="📜 可回退的历史检查点 (Undo History)", border_style="yellow")
    table.add_column("步骤", style="bold cyan", justify="center")
    table.add_column("发生时间", style="dim", justify="center")
    table.add_column("操作描述", style="white", justify="left")
    table.add_column("影响文件", style="yellow", justify="left")

    for item in stack:
        table.add_row(
            f"#{item['step']}",
            item["time"],
            item["description"],
            ", ".join(item["files"]) or "-"
        )
    console.print(table)
    console.print("[dim]输入 /undo 可直接撤销最近一步修改。[/dim]")
