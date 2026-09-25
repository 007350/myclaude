import os
import sys
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.prompt import Prompt

from .config import Config
from .agent import Agent
from .ui import (
    console,
    print_welcome,
    print_info,
    print_error,
    print_mcp_servers,
    print_yolo_status,
)


def setup_interactive_config() -> Config:
    """引导用户初始化配置并写入 .env"""
    console.print("\n[bold yellow]👋 欢迎使用 MyClaude！检测到尚未配置 API Key。[/bold yellow]")
    console.print("请选择你打算使用的模型服务：")
    console.print("  [1] DeepSeek (推荐，性价比极高，直接填官方 sk-xxx)")
    console.print("  [2] OpenRouter (支持 Claude 3.5/3.7 Sonnet、GPT-4o)")
    console.print("  [3] 本地 Ollama (完全离线，免费无须 Key)")
    console.print("  [4] 自定义 / 其他兼容 OpenAI 接口")

    choice = Prompt.ask("请输入选项", choices=["1", "2", "3", "4"], default="1")

    base_url = "https://api.deepseek.com/v1"
    model_name = "deepseek-chat"
    api_key = ""

    if choice == "1":
        base_url = "https://api.deepseek.com/v1"
        model_name = "deepseek-chat"
        api_key = Prompt.ask("请输入你的 DeepSeek API Key (sk-...)")
    elif choice == "2":
        base_url = "https://openrouter.ai/api/v1"
        model_name = Prompt.ask("请输入模型名", default="anthropic/claude-3.5-sonnet")
        api_key = Prompt.ask("请输入你的 OpenRouter API Key (sk-or-...)")
    elif choice == "3":
        base_url = "http://localhost:11434/v1"
        model_name = Prompt.ask("请输入 Ollama 本地模型名称", default="qwen2.5-coder:7b")
        api_key = "ollama"
    else:
        base_url = Prompt.ask("请输入 Base URL", default="https://api.openai.com/v1")
        model_name = Prompt.ask("请输入 Model Name", default="gpt-4o")
        api_key = Prompt.ask("请输入 API Key")

    env_content = f"""# MyClaude 自动生成的配置文件
OPENAI_API_KEY={api_key.strip()}
OPENAI_BASE_URL={base_url.strip()}
MODEL_NAME={model_name.strip()}
MAX_STEPS=30
"""
    env_file = Path.cwd() / ".env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)

    print_info(f"配置已保存至: {env_file}")
    return Config.load()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    config = Config.load()

    # 如果未配置，触发交互式引导
    if not config.is_configured():
        config = setup_interactive_config()

    # 初始化历史文件
    history_file = Path.home() / ".myclaude" / "history.txt"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(history_file)))

    # 初始化 MCP 插件管理器（使用全局共享实例，支持 Agent 运行时动态热插拔）
    from .mcp import default_mcp_manager as mcp_manager
    mcp_count = mcp_manager.load_and_connect_all()

    # 启动侧边伴生窗口通信 IPC 服务
    from .core import ipc_server
    try:
        sidecar_port = ipc_server.start()
    except Exception:
        sidecar_port = 0

    agent = Agent(config)
    print_welcome(model_name=config.model_name, cwd=os.getcwd(), mcp_count=mcp_count, sidecar_port=sidecar_port)

    try:
        while True:
            try:
                # 优雅的输入框提示符
                user_input = session.prompt("\n👉 myclaude > ").strip()
                if not user_input:
                    continue

                # 处理快捷命令
                cmd_lower = user_input.lower()
                if cmd_lower in ("/exit", "/quit", "exit", "quit"):
                    console.print("[dim]👋 再见！[/dim]")
                    break
                elif cmd_lower in ("/clear", "/reset"):
                    agent.reset()
                    print_info("已清空上下文历史记录。")
                    continue
                elif cmd_lower in ("/model", "/config"):
                    print_info(
                        f"当前模型: [bold green]{config.model_name}[/bold green]\n"
                        f"接口地址: [bold cyan]{config.base_url}[/bold cyan]\n"
                        f"工作目录: [bold yellow]{os.getcwd()}[/bold yellow]"
                    )
                    continue
                elif cmd_lower in ("/yolo", "/mode"):
                    is_yolo = agent.permission_mgr.toggle_yolo()
                    print_yolo_status(is_yolo)
                    continue
                elif cmd_lower in ("/compact", "/compress"):
                    agent.manual_compact()
                    continue
                elif cmd_lower in ("/mcp", "/plugins"):
                    print_mcp_servers(mcp_manager.get_server_stats())
                    continue
                elif cmd_lower in ("/help", "help"):
                    console.print(
                        "[bold cyan]可用命令:[/bold cyan]\n"
                        "  /compact: 手动触发智能上下文微摘要压缩 (保留 KV Cache 静态前缀)\n"
                        "  /yolo   : 切换 YOLO 极速放行模式 / 安全确认模式\n"
                        "  /mcp    : 查看已挂载的 MCP 外部工具与服务状态\n"
                        "  /clear  : 清空当前多轮对话记忆\n"
                        "  /model  : 查看当前模型与 API 配置\n"
                        "  /exit   : 退出程序\n"
                        "直接输入日常开发需求，例如：\n"
                        "  - '帮我写一个快速排序算法并测试'\n"
                        "  - '检查当前目录下的 git 状态'\n"
                        "  - '重构某个文件中的某函数'\n"
                    )
                    continue

                # 执行智能体多轮推理
                agent.step(user_input)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]操作已取消或退出。[/dim]")
                break
            except Exception as e:
                print_error(f"发生未预期错误: {str(e)}")
    finally:
        mcp_manager.shutdown()
        ipc_server.stop()


if __name__ == "__main__":
    main()
