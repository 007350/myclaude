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


def print_welcome(model_name: str, cwd: str, mcp_count: int = 0, sidecar_port: int = 0):
    text = Text()
    text.append("🤖 MyClaude Agent CLI\n", style="bold cyan")
    text.append(f"• 模型: {model_name}\n", style="green")
    text.append(f"• 工作区: {cwd}\n", style="yellow")
    if mcp_count > 0:
        text.append(f"• MCP 插件: 已挂载 ({mcp_count} 个外部工具)\n", style="bold magenta")
    if sidecar_port > 0:
        text.append(f"• 伴生窗口: 监听端口 {sidecar_port}（可在侧边终端运行 python sidecar.py 连通）\n", style="bold blue")
    text.append("• 输入具体任务，Agent 会自主思考、读取与编写代码、执行命令\n", style="dim")
    text.append("• 常用命令: /yolo (极速放行), /mcp (查看插件), /clear (清空上下文), /exit (退出)", style="dim italic")

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
