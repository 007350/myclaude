from .registry import registry, ToolRegistry
# 导入所有工具模块以触发自动注册
from . import bash
from . import file_ops
from . import mcp_ops

__all__ = ["registry", "ToolRegistry", "bash", "file_ops", "mcp_ops"]
