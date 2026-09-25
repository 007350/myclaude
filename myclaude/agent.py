import os
import json
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI

from .config import Config
from .tools import registry
from .security import PermissionManager, PermissionMode
from .ui import (
    console,
    print_assistant_message,
    print_tool_call,
    print_tool_result,
    ask_permission_choice,
    print_yolo_status,
    print_error,
    print_info,
)


class Agent:
    def __init__(self, config: Config, permission_mgr: Optional[PermissionManager] = None):
        self.config = config
        self.permission_mgr = permission_mgr or PermissionManager(
            PermissionMode.YOLO if config.auto_confirm else PermissionMode.NORMAL
        )
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
        self.messages: List[Dict[str, Any]] = []
        self.reset()

    def _build_system_prompt(self) -> str:
        cwd = os.getcwd()
        os_name = platform.system()
        files = []
        try:
            for item in Path(cwd).iterdir():
                if not item.name.startswith("."):
                    files.append(f"{item.name}{'/' if item.is_dir() else ''}")
        except Exception:
            pass

        files_summary = ", ".join(files[:30]) if files else "(当前目录为空)"

        return f"""你是一个运行在本地终端的自主编程 Agent 助手（类似于 Claude Code）。
你有权限查看、编辑本地文件以及在用户电脑上执行命令行指令来解决用户的软件工程与开发任务。

### 运行环境:
- 操作系统: {os_name}
- 当前工作目录: {cwd}
- 当前目录文件: {files_summary}

### 工具使用核心准则:
1. **优先使用 edit_file 而非 write_file**: 修改已有文件时，必须使用 edit_file 进行精准字符串替换。不要全量覆盖已有文件，以避免丢失上下文或无谓浪费 Token。
2. **代码修改前务必先看后改**: 使用 read_file 仔细确认已有代码的缩进、换行和上下文，确保 old_str 在文件中是唯一的。
3. **闭环验证**: 当用户要求修复 Bug、运行测试或构建项目时，主动使用 run_command 执行命令检查验证，确认修改无误后再给用户反馈。
4. **简洁专业**: 保持回复简练，直奔主题。在工具调用期间不用废话，直接调用工具；在任务完成时简明汇报修改内容。
5. **语言风格**: 默认使用用户使用的语言（中文）。
6. **自主能力扩展 (MCP 自进化)**: 当用户需要某项你原生不具备的能力（如查询网络特定数据、调用特殊第三方库、数据库交互等），或者明确要求你给自己添加新能力时，你可以使用 `create_python_mcp_server` 工具自主编写一段完整的 FastMCP Python 代码动态挂载为你的新工具，或者使用 `add_mcp_server` 接入外部服务。一旦添加成功，你可以在当前对话中立即调用它！
"""

    def reset(self):
        """重置上下文历史"""
        self.messages = [
            {"role": "system", "content": self._build_system_prompt()}
        ]

    def step(self, user_input: str):
        """执行单轮用户任务，进入自主思考与工具循环"""
        self.messages.append({"role": "user", "content": user_input})

        step_count = 0
        while step_count < self.config.max_steps:
            step_count += 1

            # 呼叫模型
            try:
                with console.status("[bold green]Agent 正在思考中...[/bold green]", spinner="dots"):
                    response = self.client.chat.completions.create(
                        model=self.config.model_name,
                        messages=self.messages,
                        tools=registry.get_schemas(),
                        tool_choice="auto",
                    )
            except Exception as e:
                print_error(f"调用模型接口失败: {str(e)}")
                return

            choice = response.choices[0]
            message = choice.message

            # 如果模型给出了文本回复
            if message.content:
                print_assistant_message(message.content)

            # 将 assistant 消息存入历史记录
            assistant_msg_dict: Dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }

            if message.tool_calls:
                assistant_msg_dict["tool_calls"] = [
                    tc.model_dump() for tc in message.tool_calls
                ]

            self.messages.append(assistant_msg_dict)

            # 如果模型没有调用任何工具，说明当前任务完成
            if not message.tool_calls:
                break

            # 逐个执行工具调用
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                call_id = tool_call.id

                # 解析工具参数
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception as e:
                    args = {}
                    print_error(f"解析工具参数失败: {str(e)}")

                print_tool_call(func_name, args)

                # 权限拦截判断
                execute_allowed = True
                should_ask, desc = self.permission_mgr.should_ask(func_name, args)
                if should_ask:
                    choice = ask_permission_choice(desc)
                    if choice == "a":
                        self.permission_mgr.mode = PermissionMode.YOLO
                        print_yolo_status(True)
                        execute_allowed = True
                    elif choice == "y":
                        execute_allowed = True
                    else:
                        execute_allowed = False

                if not execute_allowed:
                    tool_output = "用户拒绝了执行此操作的权限。"
                else:
                    with console.status(f"[bold yellow]正在执行工具: {func_name}...[/bold yellow]", spinner="line"):
                        tool_output = registry.execute(func_name, args)

                # 展示工具结果
                print_tool_result(func_name, tool_output)

                # 将工具执行结果存入上下文
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_output,
                })
        
        if step_count >= self.config.max_steps:
            print_info(f"已达到单次任务最大步数限制 ({self.config.max_steps} 步)。")
