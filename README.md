# MyClaude: 本地终端 AI 编程智能体 (Claude Code Python 版)

这是一个受 **Claude Code** 启发、基于 **Python** 打造的本地终端自主编程 Agent。它能够在本地终端通过 ReAct 循环（思考 $\to$ 调用工具 $\to$ 执行 $\to$ 验证），自主完成代码阅读、精准替换、文件修改以及命令行测试执行。

---

## 🌟 核心特性

- **ReAct 自主循环**：具备多轮自主思考与工具调用链能力，自动修复 Bug，任务未完成不终止。
- **Claude Code 核心同款工具集**：
  - `run_command`：在 Windows (PowerShell) / Linux / macOS 下执行终端命令，自带超大输出截断与防爆保护。
  - `read_file`：精准行号切片查看，防止大文件爆 Token。
  - `write_file`：创建与全量覆写文件。
  - `edit_file`：**核心精准匹配替换 (`str_replace`)**，修改已有代码时不全量覆写，保持代码上下文稳定且节省 Token。
  - `list_dir`：目录树浏览与代码定位。
- **⚡ YOLO 极速模式与权限守卫 (Feature 6)**：
  - **安全模式 (默认)**：智能拦截高危指令（如破坏性命令、格式化、不可逆操作），弹出 `[y] 单次允许 / [a] 始终允许(YOLO) / [n] 拒绝` 确认选项。
  - **YOLO 模式**：通过输入 `/yolo` 一键开启极速放行，全自动静默执行所有操作，适合信任环境下的快速自主开发。
- **🔌 官方 MCP (Model Context Protocol) 插件协议支持 (Feature 5)**：
  - 原生集成 Anthropic 官方 MCP 标准，支持挂载任意本地或第三方 MCP 外部工具服务（如浏览器、数据库、外部 API、计算器等）。
  - 支持在当前目录放置 `mcp.json` 自动发现并挂载外部工具。
- **🧬 Agent 自主构建并加载 MCP 能力 (Self-Evolution)**：
  - **`create_python_mcp_server`**：Agent 可以根据你的业务需求，自主编写 FastMCP Python 代码，自动创建服务文件、更新 `mcp.json`，并在当前会话中**零重启动态热加载**！
  - **`add_mcp_server`**：Agent 可直接挂载外部已有 MCP 命令（如 npx 工具包），立刻获得新技能。
- **高颜值终端体验**：
  - 使用 `rich` 呈现 Markdown 高亮、工具调用卡片与思考加载动画，全平台（含 Windows）UTF-8/Emoji 防乱码适配。
  - 使用 `prompt_toolkit` 提供支持光标移动、历史记录查看（上下键）的友好输入行。
- **多模型兼容**：
  - 支持 **DeepSeek (推荐，性价比极高)**、**Claude 3.5/3.7 (通过 OpenRouter 或代理)**、**OpenAI**、以及 **本地 Ollama (完全离线免费)**。

---

## 🚀 快速开始

### 1. 运行方式
进入当前项目目录并运行：
```bash
python main.py
```
> 若第一次运行，系统会自动弹出引导，让你选择要接入的模型并保存到本地 `.env` 文件中。

### 2. 手动配置 `.env`
复制 `.env.example` 为 `.env`：
```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

---

## 🔌 MCP 插件扩展指南

在项目根目录下创建 `mcp.json`（已附带开箱即用的 [mcp.json](file:///D:/myclaude/mcp.json) 与示例服务 [examples/sample_mcp_server.py](file:///D:/myclaude/examples/sample_mcp_server.py)）：

```json
{
  "mcpServers": {
    "sample-tools": {
      "command": "python",
      "args": ["examples/sample_mcp_server.py"]
    }
  }
}
```

启动程序时，Agent 将自动连通配置的 MCP 服务，并将其注册为 Agent 的可用工具！输入 `/mcp` 即可随时查看当前已挂载的服务与工具清单。

---

## 🎮 常用快捷命令

在 `myclaude >` 提示符下：
- `/yolo` 或 `/mode`：**一键切换 YOLO 极速模式与安全确认模式**
- `/mcp` 或 `/plugins`：**查看已挂载的 MCP 服务与外部工具列表**
- `/clear` 或 `/reset`：清空当前的对话上下文记忆
- `/model` 或 `/config`：查看当前正在使用的模型与配置
- `/help`：查看所有帮助说明
- `/exit` 或 `/quit`：退出程序
