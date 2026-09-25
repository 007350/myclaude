import subprocess
import os
import platform
from .registry import registry

# 危险命令特征检查
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "format ",
    "del /f /s /q c:",
    ":(){ :|:& };:",
    "mkfs",
    "dd if=",
]


def is_potentially_dangerous(command: str) -> bool:
    cmd_lower = command.lower()
    return any(p in cmd_lower for p in DANGEROUS_PATTERNS)


def truncate_output(text: str, max_lines: int = 150, max_chars: int = 12000) -> str:
    """智能截断超大输出，保留首尾，防止撑爆上下文"""
    if len(text) <= max_chars and text.count("\n") <= max_lines:
        return text

    lines = text.splitlines()
    if len(lines) > max_lines:
        half = max_lines // 2
        truncated_count = len(lines) - max_lines
        lines = (
            lines[:half]
            + [f"\n... [已截断 {truncated_count} 行长日志] ...\n"]
            + lines[-half:]
        )
        text = "\n".join(lines)

    if len(text) > max_chars:
        half_char = max_chars // 2
        text = text[:half_char] + "\n... [已截断中间超长文本] ...\n" + text[-half_char:]

    return text


@registry.register(
    name="run_command",
    description="在本地系统运行 shell 命令行。可用于查看状态、执行测试、git 操作、构建等。Windows 下使用 PowerShell 执行。"
)
def run_command(command: str) -> str:
    """运行终端命令并返回输出"""
    is_win = platform.system() == "Windows"
    shell_cmd = ["powershell", "-NoProfile", "-Command", command] if is_win else ["bash", "-c", command]

    try:
        process = subprocess.run(
            shell_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            cwd=os.getcwd(),
            encoding="utf-8",
            errors="replace"
        )
        output = process.stdout
        if process.stderr:
            output += ("\n[Stderr]:\n" + process.stderr)

        output = output.strip()
        if not output:
            output = f"(命令执行成功，无输出，退出码: {process.returncode})"
        else:
            if process.returncode != 0:
                output = f"[退出码 {process.returncode}]\n" + output

        return truncate_output(output)
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时 (超过 120 秒已自动终止)"
    except Exception as e:
        return f"命令执行异常: {str(e)}"
