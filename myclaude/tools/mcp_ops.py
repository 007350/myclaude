import sys
import os
from pathlib import Path
from typing import List, Optional, Dict
from .registry import registry
from ..mcp import default_mcp_manager


@registry.register(
    name="add_mcp_server",
    description="在当前运行会话中动态添加并连接一个新的外部 MCP 服务（如 npx 或已有脚本），并持久化到 mcp.json。添加后你将立即获得该服务提供的所有工具。"
)
def add_mcp_server(name: str, command: str, args: List[str] = None) -> str:
    """动态添加现有的 MCP 服务并立即连接"""
    args = args or []
    try:
        new_tools = default_mcp_manager.add_and_connect_server(
            name=name,
            command=command,
            args=args,
            persist=True
        )
        return (
            f"✅ 成功连接并挂载 MCP 服务 '{name}'！\n"
            f"配置已持久化至 mcp.json。\n"
            f"新激活的工具列表 ({len(new_tools)} 个): {', '.join(new_tools)}\n"
            f"你现在可以直接调用这些工具来完成用户的后续任务。"
        )
    except Exception as e:
        return f"添加 MCP 服务 '{name}' 失败: {str(e)}"


@registry.register(
    name="create_python_mcp_server",
    description="用一段完整的 FastMCP Python 代码在本地自主创建一个全新的 MCP 服务，并立即动态编译挂载至当前会话。当你需要扩展自身所不具备的能力（如查询某 API、计算、调用特定库）时，可自主编写代码并调用此工具。"
)
def create_python_mcp_server(name: str, python_code: str) -> str:
    """自主编写并动态挂载一个 Python FastMCP 服务"""
    try:
        # 确保保存目录存在
        target_dir = Path.cwd() / "custom_mcp_servers"
        target_dir.mkdir(parents=True, exist_ok=True)
        server_file = target_dir / f"{name}_server.py"

        # 检查是否包含必要的 FastMCP 启动代码，如果没有则友好提示
        if "FastMCP" not in python_code or "mcp.run" not in python_code:
            return (
                "错误: 提供的代码缺少 FastMCP 结构。标准的 FastMCP 脚本结构示例:\n"
                "from mcp.server.fastmcp import FastMCP\n"
                f"mcp = FastMCP('{name}')\n"
                "@mcp.tool()\n"
                "def my_tool(...) -> str:\n"
                "    return ...\n"
                "if __name__ == '__main__':\n"
                "    mcp.run(transport='stdio')\n"
            )

        with open(server_file, "w", encoding="utf-8") as f:
            f.write(python_code)

        # 挂载并热加载
        rel_path = f"custom_mcp_servers/{name}_server.py"
        new_tools = default_mcp_manager.add_and_connect_server(
            name=name,
            command=sys.executable,
            args=[rel_path],
            persist=True
        )

        return (
            f"🎉 成功自主创建并激活 MCP 服务 '{name}'！\n"
            f"服务文件保存于: {server_file}\n"
            f"已写入 mcp.json 配置。\n"
            f"新获得的工具列表 ({len(new_tools)} 个): {', '.join(new_tools)}\n"
            f"你现在可以立刻调用这些新工具！"
        )
    except Exception as e:
        return f"创建/挂载自定义 MCP 服务 '{name}' 失败: {str(e)}"
