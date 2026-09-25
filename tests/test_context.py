"""
Unit and integration tests for ContextManager (Context Window Pruning & Compaction)
"""
import unittest
from unittest.mock import MagicMock
from myclaude.core.context import (
    ContextManager,
    estimate_text_tokens,
    estimate_messages_tokens,
)


class TestContextManager(unittest.TestCase):
    def setUp(self):
        self.cm = ContextManager(
            soft_token_limit=500,
            hard_token_limit=1000,
            keep_recent_turns=2,
        )

    def test_token_estimation(self):
        text = "Hello world! This is a test."
        tokens = estimate_text_tokens(text)
        self.assertGreater(tokens, 0)

        # Chinese characters
        cn_text = "这是一段中文测试文本，验证分词估算"
        cn_tokens = estimate_text_tokens(cn_text)
        self.assertGreater(cn_tokens, 0)

        # Message token estimation
        messages = [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Hello!"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.py"}',
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "file contents here"},
        ]
        total_tokens = estimate_messages_tokens(messages)
        self.assertGreater(total_tokens, 20)

    def test_tier1_soft_pruning(self):
        # Create a dialogue with older bulky tool outputs
        bulky_log = "\n".join([f"Log line {i}: process working on step {i}" for i in range(50)])
        messages = [
            {"role": "system", "content": "System prompt (static cache)."},
            {"role": "user", "content": "Run build"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "run_command", "arguments": "{}"}}],
            },
            {"role": "tool", "tool_call_id": "c1", "content": bulky_log},
            {"role": "assistant", "content": "Build completed with warnings."},
            # Recent turns (keep_recent_turns = 2)
            {"role": "user", "content": "Check status"},
            {"role": "assistant", "content": "Status is clean."},
            {"role": "user", "content": "Next step?"},
        ]

        tokens_before = estimate_messages_tokens(messages)
        pruned_msgs, count = self.cm.prune_stale_tool_outputs(messages, max_tool_chars=200)
        tokens_after = estimate_messages_tokens(pruned_msgs)

        self.assertEqual(count, 1)
        self.assertLess(tokens_after, tokens_before)

        # Ensure the pruned content contains the fold marker
        tool_msg = pruned_msgs[3]
        self.assertIn("已自动折叠", tool_msg["content"])
        self.assertIn("Log line 0", tool_msg["content"])
        self.assertIn("Log line 49", tool_msg["content"])

    def test_tier2_hard_compaction_with_mock_llm(self):
        # Setup multi-turn dialogue
        messages = [
            {"role": "system", "content": "System Prompt: Root Cache Target"},
            {"role": "user", "content": "User Root Goal: Implement OAuth2 login"},
        ]
        for i in range(10):
            messages.append({"role": "assistant", "content": f"Step {i}: inspecting auth module"})
            messages.append({"role": "user", "content": f"Continue with sub-step {i}"})

        # Mock OpenAI Client
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "1. 已达成: 分析了 OAuth2 流程\n2. 状态: 基础代码已写好\n3. 遗留: 单元测试待补充"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        compacted, stats = self.cm.compact_history(mock_client, "mock-model", messages)

        self.assertTrue(stats.get("compressed"))
        self.assertGreater(stats.get("saved_tokens", 0), 0)

        # Crucial check: System prompt (messages[0]) MUST be untouched for Prefix Cache!
        self.assertEqual(compacted[0]["role"], "system")
        self.assertEqual(compacted[0]["content"], "System Prompt: Root Cache Target")

        # Root user message must be preserved
        self.assertEqual(compacted[1]["role"], "user")
        self.assertEqual(compacted[1]["content"], "User Root Goal: Implement OAuth2 login")

        # Snapshot summary injected
        self.assertIn("系统自动上下文深度压缩快照", compacted[2]["content"])
        self.assertIn("已达成: 分析了 OAuth2 流程", compacted[2]["content"])

    def test_auto_balance_thresholds(self):
        mock_client = MagicMock()

        # Below limit -> No changes
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        msgs, stats = self.cm.auto_balance(mock_client, "model", messages)
        self.assertIsNone(stats)
        self.assertEqual(len(msgs), 2)


if __name__ == "__main__":
    unittest.main()
