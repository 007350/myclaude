import os
import re
from pathlib import Path
from typing import List, Optional
from .registry import registry


IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".idea", ".vscode", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".next", ".nuxt", "target", "bin", "obj", ".myclaude"
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyd", ".exe", ".dll", ".so", ".dylib", ".bin", ".zip", ".tar",
    ".gz", ".7z", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff",
    ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".pdf", ".sqlite", ".db"
}


def is_binary_file(file_path: Path) -> bool:
    """快速探测是否为二进制文件"""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        return True


@registry.register(
    name="code_search",
    description="在工作区所有代码文件中高速检索关键词或正则表达式。自动过滤 .git、node_modules、venv 等无关目录及二进制文件。返回包含匹配行号及代码上下文。"
)
def code_search(
    query: str,
    path: str = ".",
    file_pattern: Optional[str] = None,
    is_regex: bool = False,
    case_sensitive: bool = False,
    max_results: int = 30,
) -> str:
    """
    全局代码符号与内容检索工具 (类似 ripgrep)
    """
    if not query or not query.strip():
        return "错误: 搜索关键词 (query) 不能为空。"

    root = Path(path).resolve()
    if not root.exists():
        return f"错误: 搜索根路径 '{path}' 不存在。"

    # 预编译正则或预处理关键词
    regex_pattern = None
    if is_regex:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex_pattern = re.compile(query, flags)
        except re.error as e:
            return f"正则表达式语法错误: {str(e)}"
    else:
        target_str = query if case_sensitive else query.lower()

    matches: List[str] = []
    scanned_files_count = 0
    total_matches_count = 0

    # 递归遍历文件
    for current_dir, dirs, files in os.walk(root):
        # 原地过滤被忽略的目录，阻止 os.walk 深入
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for fname in files:
            fpath = Path(current_dir) / fname
            ext = fpath.suffix.lower()
            if ext in IGNORED_EXTENSIONS:
                continue

            # 按通配符过滤文件名
            if file_pattern:
                import fnmatch
                if not fnmatch.fnmatch(fname.lower(), file_pattern.lower()):
                    continue

            # 探测二进制
            if is_binary_file(fpath):
                continue

            scanned_files_count += 1
            rel_path = fpath.relative_to(root)

            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for line_idx, line in enumerate(f, 1):
                        hit = False
                        if regex_pattern:
                            hit = bool(regex_pattern.search(line))
                        else:
                            check_line = line if case_sensitive else line.lower()
                            hit = target_str in check_line

                        if hit:
                            total_matches_count += 1
                            if len(matches) < max_results:
                                snippet = line.strip()
                                if len(snippet) > 150:
                                    snippet = snippet[:147] + "..."
                                matches.append(f"  {rel_path}:{line_idx:d}: {snippet}")
            except Exception:
                pass

    if not matches:
        return f"未找到与 '{query}' 相关的匹配项 (已扫描 {scanned_files_count} 个代码文件)。"

    header = f"🔍 找到 {total_matches_count} 处匹配 (显示前 {len(matches)} 项，共检索 {scanned_files_count} 个文件):"
    result = [header] + matches
    if total_matches_count > max_results:
        result.append(f"... (剩余 {total_matches_count - max_results} 处匹配已截断，可传入特定 file_pattern 进一步缩小范围)")

    return "\n".join(result)


@registry.register(
    name="find_files",
    description="按文件名或通配符模式（如 '*test*.py'、'*.json'、'auth*'）在工作区中极速查找文件路径。"
)
def find_files(
    pattern: str,
    path: str = ".",
    max_results: int = 50,
) -> str:
    """
    文件名与通配符快速定位工具
    """
    if not pattern or not pattern.strip():
        return "错误: 通配符模式 (pattern) 不能为空。"

    root = Path(path).resolve()
    if not root.exists():
        return f"错误: 根路径 '{path}' 不存在。"

    import fnmatch
    matched_files: List[str] = []
    scanned_count = 0

    clean_pattern = pattern.strip().lower()

    for current_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for fname in files:
            scanned_count += 1
            if fnmatch.fnmatch(fname.lower(), clean_pattern):
                fpath = Path(current_dir) / fname
                rel_path = fpath.relative_to(root)
                matched_files.append(f"  • {rel_path}")
                if len(matched_files) >= max_results:
                    break
        if len(matched_files) >= max_results:
            break

    if not matched_files:
        return f"未找到符合模式 '{pattern}' 的文件 (已检索 {scanned_count} 个文件)。"

    header = f"📁 符合模式 '{pattern}' 的文件清单 (共 {len(matched_files)} 项):"
    return "\n".join([header] + matched_files)
