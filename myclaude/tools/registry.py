import inspect
from typing import Callable, Any, Dict, List


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []

    def register(self, name: str = "", description: str = ""):
        """装饰器：注册一个 Python 函数为 Agent 工具"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip()

            # 解析函数签名生成 JSON Schema
            sig = inspect.signature(func)
            properties = {}
            required = []

            type_map = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
                list: "array",
                dict: "object",
            }

            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                json_type = type_map.get(param_type, "string")
                properties[param_name] = {
                    "type": json_type,
                    "description": f"Parameter: {param_name}",
                }
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            schema = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_desc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }

            self._tools[tool_name] = func
            self._schemas.append(schema)
            return func
        return decorator

    def register_raw_tool(self, name: str, schema: Dict[str, Any], handler: Callable):
        """注册原生已定义好的 Schema 和处理函数的工具（如 MCP 工具）"""
        self._tools[name] = handler
        self._schemas = [s for s in self._schemas if s["function"]["name"] != name]
        self._schemas.append(schema)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """严格按函数名做字典序排列，确保发给大模型的 JSON 前缀绝对一致，最大化缓存命中率"""
        return sorted(self._schemas, key=lambda s: s["function"]["name"])

    def execute(self, name: str, kwargs: Dict[str, Any]) -> str:
        if name not in self._tools:
            return f"Error: Tool '{name}' not found."
        try:
            result = self._tools[name](**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"


# 全局默认工具注册表
registry = ToolRegistry()
