"""
示例 MCP 服务端：提供时间查询与安全数学计算工具
"""
import sys
import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-tools")


@mcp.tool()
def get_current_time(offset_hours: int = 8) -> str:
    """获取当前时间。默认返回东八区北京时间 (UTC+8)。"""
    tz = datetime.timezone(datetime.timedelta(hours=offset_hours))
    now = datetime.datetime.now(tz)
    return f"当前时间 (UTC+{offset_hours}): {now.strftime('%Y-%m-%d %H:%M:%S')}"


@mcp.tool()
def calculate(expression: str) -> str:
    """计算数学表达式，例如: '2 ** 10 + 45 * 2'"""
    allowed_chars = set("0123456789+-*/(). %")
    if not all(c in allowed_chars for c in expression):
        return "错误: 表达式包含不支持的字符，仅允许数字和基础数学运算符。"
    try:
        # 仅允许受限的简单安全计算
        result = eval(expression, {"__builtins__": None}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
