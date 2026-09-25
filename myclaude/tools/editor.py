import difflib
from typing import Tuple, List, Optional


def normalize_newlines(text: str) -> Tuple[str, bool]:
    """统一将换行符转为 \n，并记录原文本是否包含 CRLF"""
    has_crlf = "\r\n" in text
    return text.replace("\r\n", "\n"), has_crlf


def restore_newlines(text: str, has_crlf: bool) -> str:
    """如果原文件是 CRLF，则将 \n 恢复为 \r\n"""
    if has_crlf:
        # 先统一成 \n 再替换为 \r\n，避免重复替换
        return text.replace("\r\n", "\n").replace("\n", "\r\n")
    return text


def find_best_matching_block(lines: List[str], target_lines: List[str]) -> Tuple[int, float, List[str]]:
    """在全文行列表中寻找与 target_lines 相似度最高的一个区间"""
    target_text = "\n".join([l.strip() for l in target_lines])
    window_size = len(target_lines)
    best_idx = -1
    best_ratio = 0.0
    best_block = []

    # 尝试 window_size, window_size ± 1
    for w in [window_size, max(1, window_size - 1), window_size + 1]:
        if w > len(lines):
            continue
        for i in range(len(lines) - w + 1):
            candidate = lines[i : i + w]
            candidate_text = "\n".join([l.strip() for l in candidate])
            ratio = difflib.SequenceMatcher(None, candidate_text, target_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = i
                best_block = candidate

    return best_idx, best_ratio, best_block


def apply_fuzzy_replace(content: str, old_str: str, new_str: str) -> Tuple[bool, str, str]:
    """
    五级容错代码替换引擎 (Fuzzy Edit Engine)
    
    返回:
      (success: bool, result_content_or_error: str, match_method: str)
    """
    if not old_str:
        return False, "错误: old_str 不能为空。", "none"

    # ========================================================
    # Level 1: 绝对精确匹配 (Exact Match)
    # ========================================================
    count = content.count(old_str)
    if count == 1:
        return True, content.replace(old_str, new_str, 1), "精确字符匹配 (Exact)"
    elif count > 1:
        return (
            False,
            f"错误: 待替换代码在文件中重复出现了 {count} 次，无法唯一确定替换位置。\n"
            f"请在 old_str 中包含更多上下文行（如前后几行代码），确保其在文件中是唯一的。",
            "none"
        )

    # ========================================================
    # Level 2: 换行符归一化匹配 (CRLF vs LF Normalization)
    # ========================================================
    norm_content, has_crlf = normalize_newlines(content)
    norm_old, _ = normalize_newlines(old_str)
    norm_new, _ = normalize_newlines(new_str)

    norm_count = norm_content.count(norm_old)
    if norm_count == 1:
        replaced = norm_content.replace(norm_old, norm_new, 1)
        return True, restore_newlines(replaced, has_crlf), "换行符自动归一化匹配 (CRLF/LF)"
    elif norm_count > 1:
        return (
            False,
            f"错误: 待替换代码在文件中重复出现了 {norm_count} 次。\n"
            f"请在 old_str 中包含更多上下文行（如前后几行代码），确保唯一性。",
            "none"
        )

    # ========================================================
    # Level 3: 行尾空白与空行容错匹配 (Trailing Whitespace Tolerance)
    # ========================================================
    content_lines = norm_content.split("\n")
    old_lines = norm_old.split("\n")
    new_lines = norm_new.split("\n")
    k = len(old_lines)

    matches_lvl3 = []
    old_rstrip = [l.rstrip() for l in old_lines]
    for i in range(len(content_lines) - k + 1):
        window_rstrip = [l.rstrip() for l in content_lines[i : i + k]]
        if window_rstrip == old_rstrip:
            matches_lvl3.append(i)

    if len(matches_lvl3) == 1:
        idx = matches_lvl3[0]
        res_lines = content_lines[:idx] + new_lines + content_lines[idx + k :]
        return True, restore_newlines("\n".join(res_lines), has_crlf), "行尾空白符容错匹配 (Trailing Whitespace)"
    elif len(matches_lvl3) > 1:
        return False, f"错误: 待替换代码匹配到 {len(matches_lvl3)} 处位置，无法唯一确定，请增加前后上下文。", "none"

    # ========================================================
    # Level 4: 相对缩进容错匹配 (Indentation Invariant Match)
    # ========================================================
    matches_lvl4 = []
    old_stripped = [l.strip() for l in old_lines]
    for i in range(len(content_lines) - k + 1):
        window_stripped = [l.strip() for l in content_lines[i : i + k]]
        if window_stripped == old_stripped:
            matches_lvl4.append(i)

    if len(matches_lvl4) == 1:
        idx = matches_lvl4[0]
        # 计算原代码与新代码的缩进偏差
        target_first_line = content_lines[idx]
        old_first_line = old_lines[0]
        target_indent = len(target_first_line) - len(target_first_line.lstrip())
        old_indent = len(old_first_line) - len(old_first_line.lstrip())
        indent_delta = target_indent - old_indent

        aligned_new_lines = []
        for line in new_lines:
            if not line.strip():
                aligned_new_lines.append("")
            elif indent_delta > 0:
                aligned_new_lines.append((" " * indent_delta) + line)
            elif indent_delta < 0:
                dedent = min(-indent_delta, len(line) - len(line.lstrip()))
                aligned_new_lines.append(line[dedent:])
            else:
                aligned_new_lines.append(line)

        res_lines = content_lines[:idx] + aligned_new_lines + content_lines[idx + k :]
        return True, restore_newlines("\n".join(res_lines), has_crlf), "缩进自动对齐容错匹配 (Indentation Shift)"
    elif len(matches_lvl4) > 1:
        return False, f"错误: 待替换代码在忽略缩进后匹配到 {len(matches_lvl4)} 处，请补充更多行锁定位置。", "none"

    # ========================================================
    # Level 5: 高置信度模糊相似度匹配 (Fuzzy Sequence Matcher >= 88%)
    # ========================================================
    best_idx, best_ratio, best_block = find_best_matching_block(content_lines, old_lines)
    if best_ratio >= 0.88:
        w = len(best_block)
        res_lines = content_lines[:best_idx] + new_lines + content_lines[best_idx + w :]
        pct = round(best_ratio * 100, 1)
        return True, restore_newlines("\n".join(res_lines), has_crlf), f"高置信度模糊相似匹配 (相似度: {pct}%)"

    # ========================================================
    # Level 6: 终极智能诊断与引导报错
    # ========================================================
    diagnostic_msg = [
        "错误: 待替换的 old_str 在目标文件中未找到。",
    ]
    if best_idx >= 0 and best_ratio >= 0.50:
        pct = round(best_ratio * 100, 1)
        start_line = best_idx + 1
        end_line = best_idx + len(best_block)
        snippet = "\n".join(f"{start_line + j:4d} | {best_block[j]}" for j in range(len(best_block)))
        diagnostic_msg.extend([
            f"\n💡 我们在文件第 {start_line}-{end_line} 行附近找到了最接近的代码片段 (相似度 {pct}%):",
            "--------------------------------------------------",
            snippet,
            "--------------------------------------------------",
            "建议: 请核对上述真实代码并精确引用后重新调用 edit_file。"
        ])
    else:
        diagnostic_msg.append("建议: 请先使用 read_file 工具查看目标文件的确切行内容与上下文。")

    return False, "\n".join(diagnostic_msg), "none"
