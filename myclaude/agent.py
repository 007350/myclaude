import os
import json
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from .config import Config
from .tools import registry
from .core import (
    shared_state,
    robust_json_parse,
    normalize_parameters,
    ContextManager,
    load_claude_md,
    default_skill_manager,
    default_snapshot_manager,
)
from .ui import (
    console,
    print_assistant_message,
    print_tool_call,
    print_tool_result,
    ask_permission_choice,
    print_yolo_status,
    print_error,
    print_info,
    print_cache_stats,
    print_compaction_card,
    print_skill_activation,
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
        self.context_mgr = ContextManager()
        self.skill_mgr = default_skill_manager
        self.snapshot_mgr = default_snapshot_manager
        self.claude_md_paths: List[Path] = []
        self.messages: List[Dict[str, Any]] = []
        self.reset()

    def undo(self) -> Tuple[bool, str, List[Path]]:
        """执行秒级原子回退，并在上下文工作记忆中同步撤销通知"""
        ok, msg, reverted = self.snapshot_mgr.rollback_latest()
        if ok and reverted:
            reverted_names = ", ".join([p.name for p in reverted])
            self.messages.append({
                "role": "user",
                "content": f"[系统指令: 用户刚刚执行了 /undo 撤回了最近的文件修改，以下文件已原子还原至修改前状态: {reverted_names}。请分析为何之前的修改未达预期，并换一种新的实现策略。]"
            })
        return ok, msg, reverted

    def manual_compact(self) -> Dict[str, Any]:
        """手动触发深度上下文微摘要压缩"""
        self.messages, stats = self.context_mgr.compact_history(
            self.client, self.config.model_name, self.messages
        )
        if stats and stats.get("compressed"):
            print_compaction_card(stats)
        elif stats:
            print_info(stats.get("reason", "无需压缩或压缩未产生变化"))
        return stats

    def activate_skill(self, name: str) -> bool:
        """用户或命令显式手动激活指定技能"""
        ok, content = self.skill_mgr.activate_skill(name)
        if ok:
            print_skill_activation(name, content)
            self.messages.append({
                "role": "user",
                "content": f"[用户手动激活专业领域技能规范]:\n{content}\n\n请在接下来的任务推进中严格遵循上述规范与操作指引！"
            })
            return True
        else:
            print_error(content)
            return False

    def _build_system_prompt(self) -> str:
        cwd = os.getcwd()
        os_name = platform.system()

        # 加载 CLAUDE.md 规范 (项目级与全局级)
        claude_md_content, loaded_paths = load_claude_md(Path(cwd))
        self.claude_md_paths = loaded_paths

        claude_md_section = ""
        if claude_md_content:
            claude_md_section = f"\n### 项目长期规范与开发指令 (CLAUDE.md):\n{claude_md_content}\n"

        # 加载轻量级 Skill 目录清单 (渐进式披露)
        skills_catalog = self.skill_mgr.get_catalog_prompt()
        skills_section = ""
        if skills_catalog:
            skills_section = f"\n{skills_catalog}\n"

        return f"""你是一个运行在本地终端的自主编程 Agent 助手（类似于 Claude Code）。
你有权限查看、编辑本地文件以及在用户电脑上执行命令行指令来解决用户的软件工程与开发任务。

### 运行环境:
- 操作系统: {os_name}
- 当前工作目录: {cwd}
- 工作区感知: 定位文件路径使用 `find_files` 或 `list_dir`；检索特定函数、类定义、报错信息或代码符号时，优先使用 `code_search` 跨文件秒级检索，切勿凭空猜测文件位置或盲目通读大量无关文件。

### 工具使用核心准则:
1. **优先使用 edit_file 而非 write_file**: 修改已有文件时，必须使用 edit_file 进行精准字符串替换。不要全量覆盖已有文件，以避免丢失上下文或无谓浪费 Token。
2. **代码修改前务必先看后改**: 使用 read_file 仔细确认已有代码的缩进、换行和上下文，确保 old_str 在文件中是唯一的。
3. **闭环验证**: 当用户要求修复 Bug、运行测试或构建项目时，主动使用 run_command 执行命令检查验证，确认修改无误后再给用户反馈。
4. **简洁专业**: 保持回复简练，直奔主题。在工具调用期间不用废话，直接调用工具；在任务完成时简明汇报修改内容。
5. **语言风格**: 默认使用用户使用的语言（中文）。
6. **自主能力扩展 (MCP 自进化)**: 当用户需要某项你原生不具备的能力（如查询网络特定数据、调用特殊第三方库、数据库交互等），或者明确要求你给自己添加新能力时，你可以使用 `create_python_mcp_server` 工具自主编写一段完整的 FastMCP Python 代码动态挂载为你的新工具，或者使用 `add_mcp_server` 接入外部服务。一旦添加成功，你可以在当前对话中立即调用它！
{claude_md_section}{skills_section}"""

    def reset(self):
        """重置上下文历史并重新装载 CLAUDE.md 与 Skills"""
        self.skill_mgr.scan_skills()
        self.messages = [
            {"role": "system", "content": self._build_system_prompt()}
        ]

    def step(self, user_input: str):
        """执行单轮用户任务，进入自主思考与工具循环"""
        self.messages.append({"role": "user", "content": user_input})
        shared_state.set_goal(user_input)

        try:
            step_count = 0
            while step_count < self.config.max_steps:
                step_count += 1
                shared_state.set_step(step_count, self.config.max_steps)

                # 检查侧边伴生窗口是否有动态下发的策略纠偏/干预指令
                steerings = shared_state.pop_all_steering()
                if steerings:
                    for s_msg in steerings:
                        console.print(f"[bold magenta]📢 [已接入侧边栏实时干预]:[/bold magenta] {s_msg}")
                        self.messages.append({
                            "role": "user",
                            "content": f"[侧边栏用户实时战略指导]: 用户在侧边窗口指示：{s_msg}。请以此为最高优先原则，动态调整你的后续思考与工具调用！"
                        })

                # 上下文拥挤度自平衡检查与梯级瘦身
                self.messages, comp_stats = self.context_mgr.auto_balance(
                    self.client, self.config.model_name, self.messages
                )
                if comp_stats:
                    print_compaction_card(comp_stats)

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

                # 统计并展示 KV Cache 缓存命中情况
                if hasattr(response, "usage") and response.usage:
                    u = response.usage
                    hit = getattr(u, "prompt_cache_hit_tokens", 0) or 0
                    total = getattr(u, "prompt_tokens", 0) or 0
                    if not hit and hasattr(u, "prompt_tokens_details") and u.prompt_tokens_details:
                        hit = getattr(u.prompt_tokens_details, "cached_tokens", 0) or 0
                    if total > 0 and hit > 0:
                        ratio = round((hit / total) * 100, 1)
                        print_cache_stats(hit, total, ratio)

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

                    # 鲁棒参数解析与自愈反馈机制
                    raw_args = tool_call.function.arguments or ""
                    parse_ok, args, parse_err = robust_json_parse(raw_args)

                    if not parse_ok:
                        print_error(f"工具 [{func_name}] 参数格式解析失败: {parse_err}")
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": f"参数格式错误: {parse_err}。请仔细核对引号与转义，重新以正确的合法 JSON 输出该工具的参数。"
                        })
                        continue

                    # 参数别名归一化（如自动对齐 file_path -> path）
                    args = normalize_parameters(func_name, args)
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
                        shared_state.set_active_tool(func_name, args)
                        try:
                            with console.status(f"[bold yellow]正在执行工具: {func_name}...[/bold yellow]", spinner="line"):
                                tool_output = registry.execute(func_name, args)
                        finally:
                            shared_state.clear_active_tool()

                    # 展示工具结果
                    print_tool_result(func_name, tool_output)

                    # 将工具执行结果存入上下文
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_output,
                    })

                # 检查本轮工具执行是否产生了文件写入/修改，若有则打包提交为一个原子 Checkpoint
                if self.snapshot_mgr.has_pending():
                    self.snapshot_mgr.commit_checkpoint(f"第 {step_count} 轮文件修改")

            if step_count >= self.config.max_steps:
                print_info(f"已达到单次任务最大步数限制 ({self.config.max_steps} 步)。")
        finally:
            shared_state.set_status("IDLE")
            shared_state.clear_active_tool()
