import re
import json
from typing import Tuple, Dict, Any


COMMON_PARAM_ALIASES = {
    "path": ["file_path", "filepath", "filename", "file", "target_path", "target_file"],
    "old_str": ["old_string", "search", "target_str", "target_string", "old_code", "old", "original"],
    "new_str": ["new_string", "replace", "new_code", "replacement", "new", "updated"],
    "command": ["cmd", "shell_cmd", "shell_command", "script", "exec"],
    "content": ["text", "code", "file_content", "body"],
}


def repair_json_string(raw: str) -> str:
    """尝试清理和修复常见的 LLM JSON 瑕疵"""
    cleaned = raw.strip()

    # 1. 剥离外层可能的 Markdown 代码块标记 ```json ... ```
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # 2. 消除尾随逗号 (Trailing Commas): 例如 `{"a": 1,}` 或 `[1, 2,]`
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    return cleaned


def robust_json_parse(raw: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    鲁棒的多阶段 JSON 解析器
    返回: (成功: bool, 解析字典: dict, 错误描述: str)
    """
    if not raw or not raw.strip():
        return True, {}, ""

    # Phase 1: 原生精准解析 (最快)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return True, data, ""
    except Exception:
        pass

    # Phase 2: 消除 Markdown 与尾随逗号后尝试
    repaired = repair_json_string(raw)
    try:
        data = json.loads(repaired)
        if isinstance(data, dict):
            return True, data, ""
    except Exception:
        pass

    # Phase 3: 单引号尝试替换为双引号 (针对类似 {'a': 1} 的 Python 式字典)
    try:
        single_quote_fixed = repaired.replace("'", '"')
        data = json.loads(single_quote_fixed)
        if isinstance(data, dict):
            return True, data, ""
    except Exception:
        pass

    # Phase 4: 如果仍然解析失败，尝试用正则提取键值对
    try:
        extracted = {}
        # 匹配 "key": "value" 或 "key": number/boolean
        matches = re.findall(r'"([^"]+)"\s*:\s*("(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?)', repaired)
        if matches:
            for k, v in matches:
                try:
                    extracted[k] = json.loads(v)
                except Exception:
                    extracted[k] = v.strip('"')
            if extracted:
                return True, extracted, ""
    except Exception:
        pass

    return False, {}, f"JSON 解析失败: 无法将内容解析为合法的键值参数。原参数文本片段: {raw[:150]}"


def normalize_parameters(func_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    参数别名对齐器：
    自动将 LLM 幻觉出的别名（如 file_path, filename）映射回真正的标准入参名（如 path）
    """
    normalized = dict(args)

    for standard_name, aliases in COMMON_PARAM_ALIASES.items():
        if standard_name not in normalized:
            for alias in aliases:
                if alias in normalized:
                    # 发现别名，平移为标准参数名并保留原值
                    normalized[standard_name] = normalized.pop(alias)
                    break

    return normalized
