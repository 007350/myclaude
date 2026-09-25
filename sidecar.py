"""
MyClaude 伴生协同终端 (Sidecar Companion)
与主 Agent 双轨并行：共享执行黑板、实时解说进度与难点、动态下发纠偏指令
"""
import os
import sys
import time
from pathlib import Path
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from openai import OpenAI

from myclaude.config import Config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

console = Console(legacy_windows=False)


def get_ipc_port() -> int:
    port_file = Path.cwd() / ".myclaude_port"
    if port_file.exists():
        try:
            with open(port_file, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 9876


http_client = httpx.Client(trust_env=False, timeout=3.0)


def fetch_status(port: int) -> dict:
    url = f"http://127.0.0.1:{port}/api/status"
    try:
        resp = http_client.get(url)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def send_steer(port: int, message: str) -> bool:
    url = f"http://127.0.0.1:{port}/api/steer"
    try:
        resp = http_client.post(url, json={"message": message})
        return resp.status_code == 200 and resp.json().get("success", False)
    except Exception:
        return False


def send_interrupt(port: int) -> bool:
    url = f"http://127.0.0.1:{port}/api/interrupt"
    try:
        resp = http_client.post(url, json={})
        return resp.status_code == 200 and resp.json().get("success", False)
    except Exception:
        return False


def print_sidecar_welcome(port: int):
    table = Table.grid(padding=1)
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("🛰️  窗口定位:", "主 Agent 伴生协同窗口 (Sidecar Companion)")
    table.add_row("🔗 连接端口:", f"http://127.0.0.1:{port}")
    table.add_row("💡 核心功能:", "随时提问主 Agent 进度/难点、动态下发策略纠偏指令、紧急中断卡死命令")
    table.add_row("🎮 快捷命令:", "/status (状态卡片)  |  /logs (实时日志)  |  /interrupt (中断当前工具)  |  /steer <指令>")

    console.print(Panel(table, title="[bold magenta]MyClaude 双轨协同副驾驶[/bold magenta]", border_style="magenta"))


def print_status_card(data: dict):
    if not data:
        console.print("[red]无法连接到主 Agent，请确认主窗口已启动。[/red]")
        return

    table = Table(title="📊 主 Agent 实时黑板快照", border_style="cyan")
    table.add_column("属性", style="bold yellow", width=15)
    table.add_column("实时状态", style="white")

    st = data.get("status", "UNKNOWN")
    st_colored = f"[bold green]{st}[/bold green]" if st == "IDLE" else f"[bold yellow]{st} (执行中)[/bold yellow]"
    table.add_row("运行状态", st_colored)
    table.add_row("当前总目标", data.get("goal") or "(等待新任务)")
    table.add_row("执行步骤", f"第 {data.get('step', 0)} / {data.get('max_steps', 30)} 步")

    active_tool = data.get("active_tool")
    if active_tool:
        elapsed = data.get("active_tool_elapsed", 0)
        table.add_row("正在运行工具", f"[bold red]{active_tool}[/bold red] (已持续 {elapsed} 秒)")
        table.add_row("工具参数", str(data.get("active_tool_args", {})))
    else:
        table.add_row("正在运行工具", "[dim]无活跃工具[/dim]")

    table.add_row("待处理干预", f"{data.get('steering_count', 0)} 条指令排队中")
    console.print(table)


def print_logs_card(logs: list):
    if not logs:
        console.print("[dim]当前暂无实时日志。[/dim]")
        return
    text = "\n".join(logs[-30:])
    console.print(Panel(text, title="📋 主 Agent 最近实时输出日志", border_style="blue"))


def ask_companion_ai(config: Config, user_query: str, status_data: dict) -> str:
    """伴生 Agent：利用大模型基于实时黑板日志向用户做战况解读"""
    client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=30)

    recent_logs_text = "\n".join(status_data.get("recent_logs", [])[-25:]) or "(暂无日志)"

    prompt = f"""你是一个专职负责“战况解说与战略分析”的伴生协同 Agent (Sidecar Copilot)。
主 Agent 正在终端执行复杂的代码开发任务，用户正在等待。
以下是主 Agent 此时此刻的实时黑板状态快照：
- 当前总目标: {status_data.get('goal', '无')}
- 状态: {status_data.get('status', '未知')} (第 {status_data.get('step', 0)} 步)
- 正在运行的工具: {status_data.get('active_tool', '无')} (已执行 {status_data.get('active_tool_elapsed', 0)} 秒)
- 工具参数: {status_data.get('active_tool_args', {})}
- 最新截获的终端日志 (最近 25 行):
{recent_logs_text}

用户在侧边窗口向你询问：
"{user_query}"

请根据上述实时真实状态，简练、准确、接地气地解答用户的疑问：
1. 告诉用户主 Agent 正在干什么，是否正常进行还是遇到了瓶颈/错误。
2. 如果存在报错或死循环征兆，向用户指出具体难点，并建议是否需要向主 Agent 注入纠偏策略。
"""
    try:
        with console.status("[bold magenta]伴生 Agent 正在梳理主任务战况...[/bold magenta]", spinner="dots"):
            resp = client.chat.completions.create(
                model=config.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"伴生助手调用失败: {str(e)}"


def main():
    config = Config.load()
    port = get_ipc_port()

    # 尝试连接主 Agent
    status = fetch_status(port)
    if not status:
        console.print(f"[bold red]❌ 未能连接到主 Agent (端口 {port})[/bold red]")
        console.print("请确保已在主窗口执行 [bold green]python main.py[/bold green] 并保持运行，然后再打开本侧边窗口。\n")
        # 持续等待重试
        console.print("[dim]正在持续监听主窗口上线... (按 Ctrl+C 退出)[/dim]")
        while not status:
            time.sleep(1.5)
            port = get_ipc_port()
            status = fetch_status(port)
        console.print("[bold green]✅ 已成功检测并连接到主 Agent！[/bold green]\n")

    print_sidecar_welcome(port)

    history_file = Path.home() / ".myclaude" / "sidecar_history.txt"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(history_file)))

    while True:
        try:
            user_input = session.prompt("\n💬 sidecar > ").strip()
            if not user_input:
                continue

            cmd_lower = user_input.lower()
            if cmd_lower in ("/exit", "/quit", "exit", "quit"):
                console.print("[dim]👋 伴生协同窗口已关闭。[/dim]")
                break

            elif cmd_lower in ("/status", "/state"):
                cur_status = fetch_status(port)
                print_status_card(cur_status)
                continue

            elif cmd_lower in ("/logs", "/log"):
                cur_status = fetch_status(port)
                print_logs_card(cur_status.get("recent_logs", []))
                continue

            elif cmd_lower in ("/interrupt", "/cancel", "/stop"):
                if send_interrupt(port):
                    console.print("[bold red]⚡ 已成功下发中断请求！当前工具将被终止。[/bold red]")
                else:
                    console.print("[red]发送中断请求失败。[/red]")
                continue

            elif cmd_lower.startswith("/steer "):
                directive = user_input[7:].strip()
                if directive and send_steer(port, directive):
                    console.print(f"[bold green]🎯 干预指令已送达！主 Agent 下一步将优先采纳：[/bold green]\n  [yellow]{directive}[/yellow]")
                else:
                    console.print("[red]下发指令失败。[/red]")
                continue

            elif cmd_lower in ("/help", "help"):
                console.print(
                    "[bold cyan]伴生窗口可用指令:[/bold cyan]\n"
                    "  /status        : 查看主 Agent 实时状态卡片 (执行工具、步数、耗时)\n"
                    "  /logs          : 实时拉取最新 30 行工具输出日志\n"
                    "  /interrupt     : 强制中断当前卡住的终端命令\n"
                    "  /steer <指令>  : 强制注入战略纠偏指令 (如: /steer 不要跑全量测试，只测单个用例)\n"
                    "直接自然语言提问，例如：\n"
                    "  - '现在运行到哪一步了？'\n"
                    "  - '为什么这步跑这么久，是不是卡住了？'\n"
                    "  - '告诉他改用正则提取不要用复杂的语法树'\n"
                )
                continue

            # 自然语言：如果用户明确说“告诉他...”或“提醒他...”，自动识别为纠偏指令
            if user_input.startswith(("告诉他", "指示他", "提醒他", "让他", "改用", "别用")):
                if send_steer(port, user_input):
                    console.print(f"[bold green]🎯 已自动识别为纠偏指令并送达主 Agent：[/bold green]\n  [yellow]{user_input}[/yellow]")
                    continue

            # 否则作为战况咨询，呼叫伴生 AI 解读
            cur_status = fetch_status(port)
            if not cur_status:
                console.print("[red]主 Agent 似乎已离线，无法获取实时状态。[/red]")
                continue

            answer = ask_companion_ai(config, user_input, cur_status)
            console.print(Panel(Markdown(answer), title="[bold magenta]🛰️ 伴生 Copilot 战况解答[/bold magenta]", border_style="magenta"))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]伴生窗口已退出。[/dim]")
            break
        except Exception as e:
            console.print(f"[red]错误: {str(e)}[/red]")


if __name__ == "__main__":
    main()
