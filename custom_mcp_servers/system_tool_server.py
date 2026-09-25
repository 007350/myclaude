
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("system_tool")

@mcp.tool()
def get_system_platform() -> str:
    """获取系统平台信息"""
    import platform
    return f"Platform: {platform.system()} {platform.release()}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
