import os
import sys
import json
import asyncio
import threading
import contextlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..tools.registry import registry as default_registry, ToolRegistry
from ..ui.console import console, print_info, print_error


class AsyncWorker:
    """在后台独立线程中维持一个运行着的 asyncio 事件循环"""
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, timeout: float = 60.0):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def stop(self):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


class MCPManager:
    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or default_registry
        self.worker = AsyncWorker()
        self.servers: Dict[str, Dict[str, Any]] = {}

    def find_config_file(self) -> Optional[Path]:
        """寻找 mcp.json 配置文件"""
        candidates = [
            Path.cwd() / "mcp.json",
            Path.cwd() / ".mcp.json",
            Path.home() / ".myclaude" / "mcp.json",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def load_and_connect_all(self, config_path: Optional[Path] = None) -> int:
        """加载 mcp.json 并连接所有已配置的 MCP 服务"""
        cfg_file = config_path or self.find_config_file()
        if not cfg_file or not cfg_file.exists():
            return 0

        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print_error(f"读取 MCP 配置文件失败: {str(e)}")
            return 0

        servers_cfg = data.get("mcpServers", {})
        connected_tools_count = 0

        for server_name, server_info in servers_cfg.items():
            cmd = server_info.get("command")
            args = server_info.get("args", [])
            env = server_info.get("env", None)
            if not cmd:
                continue

            try:
                tools = self.worker.run(self._connect_server(server_name, cmd, args, env))
                connected_tools_count += len(tools)
            except Exception as e:
                print_error(f"连接 MCP 服务 '{server_name}' 失败: {str(e)}")

        return connected_tools_count

    async def _connect_server(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]]
    ) -> List[Any]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        params = StdioServerParameters(command=command, args=args, env=merged_env)
        stack = contextlib.AsyncExitStack()
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        tools_resp = await session.list_tools()
        tools_list = tools_resp.tools

        self.servers[name] = {
            "stack": stack,
            "session": session,
            "tools": tools_list,
        }

        # 将每个工具注册到 ToolRegistry
        for tool in tools_list:
            openai_tool_name = f"mcp__{name}__{tool.name}"
            schema = {
                "type": "function",
                "function": {
                    "name": openai_tool_name,
                    "description": f"[{name} MCP 工具] {tool.description or tool.name}",
                    "parameters": tool.inputSchema if hasattr(tool, "inputSchema") and tool.inputSchema else {
                        "type": "object",
                        "properties": {},
                    },
                },
            }

            def make_handler(s_name: str, t_name: str):
                return lambda **kwargs: self.call_tool(s_name, t_name, kwargs)

            self.registry.register_raw_tool(
                name=openai_tool_name,
                schema=schema,
                handler=make_handler(name, tool.name),
            )

        return tools_list

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """同步调用 MCP 工具"""
        if server_name not in self.servers:
            return f"错误: MCP 服务 '{server_name}' 未连接。"

        try:
            return self.worker.run(self._call_tool_async(server_name, tool_name, arguments))
        except Exception as e:
            return f"执行 MCP 工具 '{tool_name}' 发生异常: {str(e)}"

    async def _call_tool_async(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        session: ClientSession = self.servers[server_name]["session"]
        result = await session.call_tool(tool_name, arguments)
        
        texts = []
        if hasattr(result, "content") and result.content:
            for item in result.content:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif hasattr(item, "data"):
                    texts.append(f"[Binary/Image data: {len(item.data)} bytes]")
                else:
                    texts.append(str(item))
        
        if result.isError if hasattr(result, "isError") else False:
            return f"[MCP 执行错误]\n" + "\n".join(texts)

        return "\n".join(texts) if texts else "(MCP 工具执行完成，无文本输出)"

    def get_server_stats(self) -> Dict[str, List[str]]:
        """获取所有已挂载的 MCP 服务及其工具名称"""
        stats = {}
        for s_name, data in self.servers.items():
            stats[s_name] = [t.name for t in data["tools"]]
        return stats

    def add_and_connect_server(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        persist: bool = True,
    ) -> List[str]:
        """动态连接一个新的 MCP 服务，并可选将其持久化保存至 mcp.json"""
        # 如果已经存在旧连接，先优雅断开
        if name in self.servers:
            try:
                self.worker.run(self.servers[name]["stack"].aclose())
            except Exception:
                pass
            del self.servers[name]

        tools = self.worker.run(self._connect_server(name, command, args, env))
        tool_names = [t.name for t in tools]

        if persist:
            cfg_file = self.find_config_file() or (Path.cwd() / "mcp.json")
            data = {"mcpServers": {}}
            if cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {"mcpServers": {}}

            if "mcpServers" not in data:
                data["mcpServers"] = {}

            server_entry = {"command": command, "args": args}
            if env:
                server_entry["env"] = env
            data["mcpServers"][name] = server_entry

            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        return tool_names

    def shutdown(self):
        """关闭所有 MCP 子进程连接"""
        for s_name, data in self.servers.items():
            try:
                self.worker.run(data["stack"].aclose())
            except Exception:
                pass
        self.worker.stop()


# 全局共享默认实例
default_mcp_manager = MCPManager()
