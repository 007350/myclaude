import json
from typing import List, Dict, Any, Tuple, Optional
import tiktoken
from openai import OpenAI

from ..ui.console import console

try:
    _encoder = tiktoken.get_encoding("cl100k_base")
except Exception:
    _encoder = None


def estimate_text_tokens(text: str) -> int:
    """估算单段文本的 Token 数量"""
    if not text:
        return 0
    if _encoder:
        try:
            return len(_encoder.encode(text, disallowed_special=()))
        except Exception:
            pass
    # 兜底估算：中文字符约 1.5 token，英文约 0.25 token/char
    return max(1, len(text) // 3)


def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    """估算整组对话历史的 Token 消耗"""
    total = 0
    for msg in messages:
        # 统计 content
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_text_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += estimate_text_tokens(part["text"])

        # 统计 tool_calls 参数
        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                func = tc.get("function", {})
                total += estimate_text_tokens(func.get("name", ""))
                total += estimate_text_tokens(func.get("arguments", ""))

        total += 4  # 每条消息的基础元数据开销
    return total


class ContextManager:
    """
    工业级上下文窗口管理器 (Context Compactor & Memory Pruner)
    具备两级渐进式瘦身能力：
    1. Tier 1: 轻量陈旧工具日志折叠 (Soft Pruning) - 瞬间释放 50%+ 空间
    2. Tier 2: 深度多轮执行摘要折叠 (Hard Compaction) - 释放 80%~95% 空间，根治长任务爆窗
    """
    def __init__(
        self,
        soft_token_limit: int = 25000,
        hard_token_limit: int = 45000,
        keep_recent_turns: int = 4,
    ):
        self.soft_token_limit = soft_token_limit
        self.hard_token_limit = hard_token_limit
        self.keep_recent_turns = keep_recent_turns

    def prune_stale_tool_outputs(
        self,
        messages: List[Dict[str, Any]],
        max_tool_chars: int = 600
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Tier 1 软裁剪：将早期轮次中臃肿的工具原始输出（如大文件全文读取、长编译日志）
        折叠为保留首尾要点的紧凑摘要。
        """
        pruned_count = 0
        new_messages = []

        # 倒数保留 keep_recent_turns 条消息不做任何裁剪
        cutoff_index = max(1, len(messages) - (self.keep_recent_turns * 2))

        for idx, msg in enumerate(messages):
            if idx < cutoff_index and msg.get("role") == "tool":
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > max_tool_chars:
                    lines = content.splitlines()
                    if len(lines) > 10:
                        head = "\n".join(lines[:4])
                        tail = "\n".join(lines[-3:])
                        truncated_count = len(lines) - 7
                        compact_content = (
                            f"{head}\n"
                            f"... [历史步骤工具输出已自动折叠，省略中间 {truncated_count} 行] ...\n"
                            f"{tail}"
                        )
                        msg_copy = dict(msg)
                        msg_copy["content"] = compact_content
                        new_messages.append(msg_copy)
                        pruned_count += 1
                        continue

            new_messages.append(msg)

        return new_messages, pruned_count

    def compact_history(
        self,
        client: OpenAI,
        model_name: str,
        messages: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Tier 2 硬压缩：调用 LLM 深度合成微摘要，浓缩中间杂乱步骤
        保留：System Prompt(保持缓存)、原始用户需求、最新若干轮活跃上下文
        """
        if len(messages) <= (self.keep_recent_turns * 2) + 2:
            return messages, {"compressed": False, "reason": "历史消息过短，无需深度压缩"}

        initial_tokens = estimate_messages_tokens(messages)

        # 结构拆分
        system_msg = messages[0]
        root_user_msg = messages[1]

        # 保护最近活跃区
        split_idx = max(2, len(messages) - (self.keep_recent_turns * 2))
        middle_msgs = messages[2:split_idx]
        recent_msgs = messages[split_idx:]

        # 构造摘要抽取 Prompt
        dialogue_text = []
        for m in middle_msgs:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if m.get("tool_calls"):
                tools_called = [tc["function"]["name"] for tc in m["tool_calls"]]
                dialogue_text.append(f"[{role}] 计划调用工具: {', '.join(tools_called)}")
            if content:
                # 限制中间摘要的单条长度
                dialogue_text.append(f"[{role}]: {content[:400]}")

        dialogue_block = "\n".join(dialogue_text)
        prompt = f"""你是一个专业的任务历史浓缩专家。
用户最初的目标是: "{root_user_msg.get('content', '')}"

以下是主 Agent 刚刚执行的一段历史记录（中间已执行的若干步骤与工具操作）：
--------------------------------------------------
{dialogue_block}
--------------------------------------------------

请为上述执行过程生成一份极为紧凑的【阶段性进展浓缩摘要】，以便 Agent 在清空冗余历史后能无缝继续推进任务。
摘要必须包含且仅包含以下 3 个要点：
1. **已达成事项**: 明确已经查明了什么、创建或成功修复了哪些文件/模块。
2. **当前工作状态**: 哪些操作通过了，哪些尝试被证明无效或遭遇了挫折。
3. **遗留未决目标**: 接下来仍需解决的关键问题是什么。
保持语言客观精炼，使用 Markdown 格式，不要包含废话。"""

        try:
            with console.status("[bold yellow]🗜️  正在对历史上下文进行智能微摘要压缩...[/bold yellow]", spinner="line"):
                summary_resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
            summary_content = summary_resp.choices[0].message.content or ""
        except Exception as e:
            return messages, {"compressed": False, "error": str(e)}

        # 重构精简后的上下文列表
        compacted_messages = [
            system_msg,
            root_user_msg,
            {
                "role": "user",
                "content": f"[系统自动上下文深度压缩快照]:\n{summary_content}\n\n请以此进展摘要为基准，结合最新的上下文继续推进任务。"
            },
            {
                "role": "assistant",
                "content": "已完全吸收前期执行进度与文件变更摘要。我将基于当前状态继续执行后续任务。"
            }
        ] + recent_msgs

        final_tokens = estimate_messages_tokens(compacted_messages)
        saved_tokens = max(0, initial_tokens - final_tokens)
        ratio = round((saved_tokens / initial_tokens) * 100, 1) if initial_tokens > 0 else 0

        return compacted_messages, {
            "compressed": True,
            "before_tokens": initial_tokens,
            "after_tokens": final_tokens,
            "saved_tokens": saved_tokens,
            "ratio": ratio,
        }

    def auto_balance(
        self,
        client: OpenAI,
        model_name: str,
        messages: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        自动梯级调优入口：在每次呼叫大模型前自动检测并执行瘦身
        """
        current_tokens = estimate_messages_tokens(messages)

        # 检查是否触碰硬阈值 (Hard Limit: 触发深度压缩)
        if current_tokens >= self.hard_token_limit:
            new_msgs, stats = self.compact_history(client, model_name, messages)
            if stats.get("compressed"):
                return new_msgs, stats

        # 检查是否触碰软阈值 (Soft Limit: 触发工具日志修剪)
        if current_tokens >= self.soft_token_limit:
            pruned_msgs, count = self.prune_stale_tool_outputs(messages)
            if count > 0:
                after_tokens = estimate_messages_tokens(pruned_msgs)
                saved = current_tokens - after_tokens
                pct = round((saved / current_tokens) * 100, 1)
                return pruned_msgs, {
                    "pruned": True,
                    "before_tokens": current_tokens,
                    "after_tokens": after_tokens,
                    "saved_tokens": saved,
                    "ratio": pct,
                }

        return messages, None
