from pathlib import Path
from .registry import registry


@registry.register(
    name="read_file",
    description="读取本地文件的内容。支持指定起始行号和结束行号（从 1 开始计数），防止一次性读取超大文件。"
)
def read_file(path: str, start_line: int = 1, end_line: int = 200) -> str:
    """读取文件内容，返回带行号的文本"""
    p = Path(path).resolve()
    if not p.exists():
        return f"错误: 文件 '{path}' 不存在。"
    if p.is_dir():
        return f"错误: '{path}' 是一个目录，不能当做文件读取。请使用 list_dir 查看目录。"

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total = len(lines)
        start = max(1, start_line)
        end = min(total, end_line)

        if start > total:
            return f"文件共 {total} 行，指定起始行 {start} 超出范围。"

        output = [f"--- 文件: {p.name} (共 {total} 行，显示第 {start}-{end} 行) ---"]
        for idx in range(start - 1, end):
            output.append(f"{idx + 1:4d} | {lines[idx].rstrip()}")

        if end < total:
            output.append(f"... (剩余 {total - end} 行未显示，可传入更高 start_line 读取)")

        return "\n".join(output)
    except Exception as e:
        return f"读取文件失败: {str(e)}"


from ..core import default_snapshot_manager


@registry.register(
    name="write_file",
    description="创建或全量覆盖写入一个文件。若父级文件夹不存在将自动创建。"
)
def write_file(path: str, content: str) -> str:
    """全量写入文件"""
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        default_snapshot_manager.record_before_change(p, f"创建/全量覆盖 {p.name}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功写入文件: {path} (共 {len(content)} 字符)"
    except Exception as e:
        return f"写入文件失败: {str(e)}"


from .editor import apply_fuzzy_replace


@registry.register(
    name="edit_file",
    description="高容错替换文件中的特定代码段。具备换行符归一化(CRLF/LF)、行尾空格忽略、缩进自动对齐与模糊相似度容错能力。old_str 应尽量唯一。"
)
def edit_file(path: str, old_str: str, new_str: str) -> str:
    """高容错代码段精准替换（类似 Claude Code / Aider 的多级回退机制）"""
    p = Path(path).resolve()
    if not p.exists():
        return f"错误: 文件 '{path}' 不存在。"
    if p.is_dir():
        return f"错误: '{path}' 是一个目录，不能当做文件编辑。"

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ok, result, method = apply_fuzzy_replace(content, old_str, new_str)
        if not ok:
            return result  # 返回智能诊断信息与最相似的代码片段

        default_snapshot_manager.record_before_change(p, f"容错编辑 {p.name}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(result)

        return f"成功编辑文件: {path} (匹配机制: {method})"
    except Exception as e:
        return f"编辑文件失败: {str(e)}"


@registry.register(
    name="list_dir",
    description="列出指定目录下的文件和子目录列表。默认列出当前工作目录。"
)
def list_dir(path: str = ".") -> str:
    """列出目录结构"""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"错误: 路径 '{path}' 不存在。"
        if not p.is_dir():
            return f"错误: '{path}' 不是目录，而是一个普通文件。"

        items = sorted(list(p.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        results = [f"目录内容: {p}"]
        for item in items[:100]:  # 最多显示前 100 项
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            results.append(f"  {prefix} {item.name}")

        if len(items) > 100:
            results.append(f"  ... 还有 {len(items) - 100} 个项目未显示")

        return "\n".join(results)
    except Exception as e:
        return f"列出目录失败: {str(e)}"
