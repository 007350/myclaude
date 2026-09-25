from enum import Enum
from typing import Tuple


class PermissionMode(str, Enum):
    NORMAL = "normal"  # 安全模式：拦截高危命令 (rm, 格式化, 破坏性 git 等)
    STRICT = "strict"  # 严格模式：拦截所有终端命令和写入操作
    YOLO = "yolo"      # 极速放行模式：全自动执行，不弹窗确认


class PermissionManager:
    def __init__(self, mode: PermissionMode = PermissionMode.NORMAL):
        self.mode = mode

    def toggle_yolo(self) -> bool:
        """在当前模式与 YOLO 模式之间切换，返回切换后是否为 YOLO"""
        if self.mode == PermissionMode.YOLO:
            self.mode = PermissionMode.NORMAL
            return False
        else:
            self.mode = PermissionMode.YOLO
            return True

    def should_ask(self, tool_name: str, args: dict) -> Tuple[bool, str]:
        """
        判断某个工具调用是否需要询问用户确认。
        返回 (是否需要询问, 拦截理由/动作描述)
        """
        if self.mode == PermissionMode.YOLO:
            return False, ""

        if tool_name == "run_command":
            cmd = args.get("command", "")
            from ..tools.bash import is_potentially_dangerous
            if is_potentially_dangerous(cmd):
                return True, f"高危终端指令: [bold red]{cmd}[/bold red]"
            if self.mode == PermissionMode.STRICT:
                return True, f"终端指令: {cmd}"

        elif tool_name in ("write_file", "edit_file"):
            if self.mode == PermissionMode.STRICT:
                path = args.get("path", "")
                return True, f"修改文件: {path}"

        return False, ""
